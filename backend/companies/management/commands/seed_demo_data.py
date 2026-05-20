import random
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from analytics.search_indexer import index_ticket
from companies.models import Company, TelegramBot, UserProfile, VkBot
from tickets.models import (
    Assignment,
    ChannelMessage,
    Sentiment,
    Ticket,
    TicketResponse,
    TransportMode,
)

User = get_user_model()

DEMO_DOMAIN = "demo.transport.local"
DEMO_PREFIX = "demo_"
DEMO_TITLE_PREFIX = "[DEMO]"


@dataclass(frozen=True)
class CompanySeed:
    slug: str
    name: str
    description: str
    phone: str


COMPANY_SEEDS = [
    CompanySeed(
        "mosmetro",
        "Московский городской транспорт",
        "Единый оператор городских маршрутов, станций и пересадочных узлов.",
        "+7 495 100-10-01",
    ),
    CompanySeed(
        "neva_bus",
        "Невские автобусные линии",
        "Региональный перевозчик с городскими и пригородными маршрутами.",
        "+7 812 200-20-02",
    ),
    CompanySeed(
        "uralrail",
        "Уральские пригородные поезда",
        "Оператор пригородного железнодорожного сообщения и вокзальной поддержки.",
        "+7 343 300-30-03",
    ),
    CompanySeed(
        "volga_tram",
        "Волжский трамвай",
        "Городская трамвайная сеть с круглосуточной диспетчерской службой.",
        "+7 844 400-40-04",
    ),
]

CATEGORY_CASES = {
    Ticket.Category.COMPLAINT: [
        ("Жалоба на переполненный автобус", "Автобус пришел переполненным, пассажиры не смогли войти на остановке."),
        ("Грубое общение водителя", "Водитель резко отвечал пассажирам и отказался подсказать остановку."),
        ("Грязный салон после рейса", "В салоне мусор, сиденья грязные, ехать неприятно."),
    ],
    Ticket.Category.INCIDENT: [
        ("Дым в вагоне метро", "В вагоне появился запах гари и дым, пассажиры просят проверить состав."),
        ("Травма пассажира на остановке", "Пассажир поскользнулся у остановочного павильона, нужна помощь."),
        ("Аварийная остановка поезда", "Поезд резко остановился между станциями, люди волнуются."),
    ],
    Ticket.Category.REQUEST: [
        ("Вопрос по расписанию маршрута", "Подскажите, когда восстановят вечерний рейс после 22:00?"),
        ("Как добраться до вокзала", "Нужен маршрут до вокзала с минимальным количеством пересадок."),
        ("Уточнение по работе станции", "Станция открыта на вход в праздничные дни?"),
    ],
    Ticket.Category.PAYMENT: [
        ("Не прошла оплата картой", "Терминал списал деньги, но турникет не открылся."),
        ("Возврат за отмененный рейс", "Рейс отменили, хочу вернуть стоимость билета."),
        ("Ошибка в стоимости проезда", "В приложении показало списание выше обычного тарифа."),
    ],
    Ticket.Category.PRAISE: [
        ("Благодарность дежурному", "Спасибо сотруднику станции, быстро помог найти потерянный рюкзак."),
        ("Хорошая работа водителя", "Водитель аккуратно вел автобус и подождал пожилого пассажира."),
        ("Чистый вагон утром", "Сегодня вагон был чистый, поезд пришел точно по расписанию."),
    ],
    Ticket.Category.SUGGESTION: [
        ("Предложение добавить указатели", "Предлагаю поставить дополнительные указатели к выходам на станции."),
        ("Идея по частоте рейсов", "В часы пик можно добавить еще один автобус на маршрут."),
        ("Улучшение уведомлений", "Хотелось бы получать push-уведомления при задержке поездов."),
    ],
}

TRANSPORT_BY_CATEGORY = {
    Ticket.Category.COMPLAINT: TransportMode.BUS,
    Ticket.Category.INCIDENT: TransportMode.METRO,
    Ticket.Category.REQUEST: TransportMode.TRAIN,
    Ticket.Category.PAYMENT: TransportMode.OTHER,
    Ticket.Category.PRAISE: TransportMode.TRAM,
    Ticket.Category.SUGGESTION: TransportMode.METRO,
}

SENTIMENT_BY_CATEGORY = {
    Ticket.Category.COMPLAINT: Sentiment.NEGATIVE,
    Ticket.Category.INCIDENT: Sentiment.NEGATIVE,
    Ticket.Category.REQUEST: Sentiment.NEUTRAL,
    Ticket.Category.PAYMENT: Sentiment.NEGATIVE,
    Ticket.Category.PRAISE: Sentiment.POSITIVE,
    Ticket.Category.SUGGESTION: Sentiment.NEUTRAL,
}

GROUP_BY_CATEGORY = {
    Ticket.Category.COMPLAINT: "service",
    Ticket.Category.INCIDENT: "safety",
    Ticket.Category.REQUEST: "operations",
    Ticket.Category.PAYMENT: "service",
    Ticket.Category.PRAISE: "operations",
    Ticket.Category.SUGGESTION: "operations",
}

PRIORITY_BY_CATEGORY = {
    Ticket.Category.COMPLAINT: Ticket.Priority.MEDIUM,
    Ticket.Category.INCIDENT: Ticket.Priority.CRITICAL,
    Ticket.Category.REQUEST: Ticket.Priority.LOW,
    Ticket.Category.PAYMENT: Ticket.Priority.HIGH,
    Ticket.Category.PRAISE: Ticket.Priority.LOW,
    Ticket.Category.SUGGESTION: Ticket.Priority.LOW,
}

STATUS_FLOW = [
    Ticket.Status.NEW,
    Ticket.Status.ACK,
    Ticket.Status.IN_PROGRESS,
    Ticket.Status.RESOLVED,
    Ticket.Status.CLOSED,
]

CHANNEL_FLOW = [
    ChannelMessage.Channel.TELEGRAM,
    ChannelMessage.Channel.VK,
]


class Command(BaseCommand):
    """Наполняет локальный стенд реалистичными данными для ручной проверки."""

    help = "Создает правдоподобные демо-данные для локальной проверки интерфейса."

    def add_arguments(self, parser):
        parser.add_argument("--companies", type=int, default=4)
        parser.add_argument("--tickets", type=int, default=220)
        parser.add_argument("--password", default="DemoPass123!")
        parser.add_argument("--skip-index", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        company_count = max(1, min(options["companies"], len(COMPANY_SEEDS)))
        ticket_count = max(1, options["tickets"])
        password = options["password"]
        skip_index = options["skip_index"]

        self._clear_demo_data()
        superadmin = self._create_superadmin(password)
        companies = self._create_companies(superadmin, company_count)
        users_by_company = {
            company: self._create_company_users(company, password)
            for company in companies
        }
        self._create_bots(companies)
        tickets = self._create_tickets(companies, users_by_company, ticket_count)

        if not skip_index:
            for ticket in tickets:
                index_ticket(ticket)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready: "
                f"companies={len(companies)}, users={User.objects.filter(username__startswith=DEMO_PREFIX).count()}, "
                f"tickets={len(tickets)}, password={password}"
            )
        )
        self.stdout.write("Demo login examples:")
        self.stdout.write(f"  superadmin: demo_superadmin / {password}")
        for company in companies:
            self.stdout.write(f"  operator: demo_{company.demo_slug}_operator_1 / {password}")

    def _clear_demo_data(self):
        """Удаляет только данные прошлого demo seed, не трогая обычные записи."""

        demo_companies = Company.objects.filter(contact_email__endswith=f"@{DEMO_DOMAIN}")
        demo_users = User.objects.filter(
            Q(username__startswith=DEMO_PREFIX) | Q(email__endswith=f"@{DEMO_DOMAIN}")
        )
        demo_tickets = Ticket.objects.filter(
            Q(title__startswith=DEMO_TITLE_PREFIX)
            | Q(company__in=demo_companies)
            | Q(messages__metadata__demo_seed=True)
        ).distinct()

        TicketResponse.objects.filter(
            Q(ticket__in=demo_tickets) | Q(author__in=demo_users)
        ).delete()
        Assignment.objects.filter(ticket__in=demo_tickets).delete()
        ChannelMessage.objects.filter(
            Q(metadata__demo_seed=True) | Q(ticket__in=demo_tickets)
        ).delete()
        demo_tickets.delete()
        TelegramBot.objects.filter(company__in=demo_companies).delete()
        VkBot.objects.filter(company__in=demo_companies).delete()
        UserProfile.objects.filter(user__in=demo_users).delete()
        demo_users.delete()
        demo_companies.delete()

    def _create_superadmin(self, password):
        user = User.objects.create_user(
            username="demo_superadmin",
            email=f"superadmin@{DEMO_DOMAIN}",
            password=password,
            first_name="Анна",
            last_name="Кураторова",
            is_staff=True,
            is_superuser=True,
        )
        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.SUPERADMIN,
            phone="+7 900 000-00-01",
        )
        return user

    def _create_companies(self, superadmin, count):
        companies = []
        now = timezone.now()
        for seed in COMPANY_SEEDS[:count]:
            company = Company.objects.create(
                name=seed.name,
                description=seed.description,
                status=Company.Status.ACTIVE,
                contact_email=f"{seed.slug}@{DEMO_DOMAIN}",
                contact_phone=seed.phone,
                default_ack_sla_minutes=30,
                default_resolve_sla_minutes=720,
                approved_by=superadmin,
                approved_at=now - timedelta(days=35),
            )
            company.demo_slug = seed.slug
            companies.append(company)
        return companies

    def _create_company_users(self, company, password):
        slug = company.demo_slug
        users = []
        admin = User.objects.create_user(
            username=f"demo_{slug}_admin",
            email=f"admin.{slug}@{DEMO_DOMAIN}",
            password=password,
            first_name="Мария",
            last_name="Администраторова",
            is_staff=True,
        )
        UserProfile.objects.create(
            user=admin,
            company=company,
            role=UserProfile.Role.COMPANY_ADMIN,
            phone="+7 900 100-00-01",
        )
        users.append(admin)

        names = [
            ("Илья", "Соколов"),
            ("Елена", "Морозова"),
            ("Денис", "Крылов"),
        ]
        for index, (first_name, last_name) in enumerate(names, start=1):
            user = User.objects.create_user(
                username=f"demo_{slug}_operator_{index}",
                email=f"operator{index}.{slug}@{DEMO_DOMAIN}",
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            UserProfile.objects.create(
                user=user,
                company=company,
                role=UserProfile.Role.OPERATOR,
                phone=f"+7 900 100-0{index}-0{index}",
            )
            users.append(user)
        return users

    def _create_bots(self, companies):
        for index, company in enumerate(companies, start=1):
            TelegramBot.objects.create(
                company=company,
                bot_token=f"1000{index}:demo-token-{company.demo_slug}",
                bot_username=f"{company.demo_slug}_support_bot",
                chat_ids=[f"-100200300{index}"],
                discussion_chat_ids=[f"-100200400{index}"],
                allow_direct=True,
                status=TelegramBot.Status.ACTIVE,
            )
            VkBot.objects.create(
                company=company,
                community_token=f"vk-demo-token-{company.demo_slug}",
                community_id=str(700000 + index),
                community_name=f"{company.name}: поддержка",
                status=VkBot.Status.ACTIVE,
            )

    def _create_tickets(self, companies, users_by_company, count):
        """Равномерно распределяет обращения по компаниям, статусам и тематикам."""

        randomizer = random.Random(42)
        categories = list(CATEGORY_CASES.keys())
        now = timezone.now()
        tickets = []
        company_ticket_numbers = {company.id: 0 for company in companies}

        for index in range(1, count + 1):
            company = companies[(index - 1) % len(companies)]
            company_ticket_numbers[company.id] += 1
            company_ticket_number = company_ticket_numbers[company.id]
            users = users_by_company[company]
            operator = users[1 + ((company_ticket_number - 1) % 3)]
            category = categories[(company_ticket_number - 1) % len(categories)]
            title, payload = randomizer.choice(CATEGORY_CASES[category])
            status = STATUS_FLOW[(company_ticket_number - 1) % len(STATUS_FLOW)]
            priority = self._priority_for(category, company_ticket_number)
            created_at = now - timedelta(
                days=randomizer.randint(0, 29),
                hours=randomizer.randint(0, 23),
                minutes=randomizer.randint(0, 55),
            )
            acknowledged_at, resolved_at = self._timestamps_for_status(
                status, created_at, priority
            )
            ack_deadline = created_at + timedelta(minutes={1: 60, 2: 30, 3: 15, 4: 5}[priority])
            resolve_deadline = created_at + timedelta(minutes={1: 1440, 2: 720, 3: 240, 4: 60}[priority])

            ticket = Ticket.objects.create(
                title=title,
                category=category,
                priority=priority,
                status=status,
                sentiment=SENTIMENT_BY_CATEGORY[category],
                is_transport=True,
                transport_mode=TRANSPORT_BY_CATEGORY[category],
                assigned_group=GROUP_BY_CATEGORY[category],
                assigned_to=operator if status != Ticket.Status.NEW else None,
                company=company,
                ack_deadline=ack_deadline,
                resolve_deadline=resolve_deadline,
                acknowledged_at=acknowledged_at,
                resolved_at=resolved_at,
            )
            Ticket.objects.filter(pk=ticket.pk).update(
                created_at=created_at,
                updated_at=resolved_at or acknowledged_at or created_at,
            )
            ticket.refresh_from_db()

            message = self._create_message(
                ticket,
                payload,
                index,
                company_ticket_number,
                created_at,
            )
            if status != Ticket.Status.NEW:
                Assignment.objects.create(
                    ticket=ticket,
                    assignee=operator.get_full_name() or operator.username,
                    channel="queue",
                    notes="Назначено автоматически по категории обращения.",
                )
            if status in {Ticket.Status.IN_PROGRESS, Ticket.Status.RESOLVED, Ticket.Status.CLOSED}:
                self._create_response(ticket, message, operator, index, acknowledged_at or created_at)

            tickets.append(ticket)
        return tickets

    def _priority_for(self, category, index):
        priority = PRIORITY_BY_CATEGORY[category]
        if category == Ticket.Category.COMPLAINT and index % 7 == 0:
            return Ticket.Priority.HIGH
        if category == Ticket.Category.REQUEST and index % 11 == 0:
            return Ticket.Priority.MEDIUM
        return priority

    def _timestamps_for_status(self, status, created_at, priority):
        if status == Ticket.Status.NEW:
            return None, None

        ack_minutes = 4 if priority == Ticket.Priority.CRITICAL else 18 + priority * 3
        acknowledged_at = created_at + timedelta(minutes=ack_minutes)
        if status in {Ticket.Status.ACK, Ticket.Status.IN_PROGRESS}:
            return acknowledged_at, None

        resolved_hours = 1 if priority == Ticket.Priority.CRITICAL else 4 + priority * 2
        resolved_at = acknowledged_at + timedelta(hours=resolved_hours)
        return acknowledged_at, resolved_at

    def _create_message(self, ticket, payload, index, channel_number, created_at):
        channel = CHANNEL_FLOW[(channel_number - 1) % len(CHANNEL_FLOW)]
        metadata = {
            "demo_seed": True,
            "source": "seed_demo_data",
            "chat_id": -1002003000 - index,
            "peer_id": 2000000000 + index,
            "conversation_message_id": index,
            "attachments": [],
        }
        if index % 9 == 0:
            metadata["attachments"] = [{"type": "photo", "file_id": f"demo-photo-{index}"}]

        message = ChannelMessage.objects.create(
            external_id=f"demo-{channel}-{index}",
            channel=channel,
            author=f"passenger_{1000 + index}",
            payload=payload,
            metadata=metadata,
            received_at=created_at - timedelta(minutes=2),
            is_transport=ticket.is_transport,
            is_comment=channel == ChannelMessage.Channel.TELEGRAM and index % 3 == 0,
            transport_mode=ticket.transport_mode,
            source_chat_id=str(metadata["chat_id"] if channel == ChannelMessage.Channel.TELEGRAM else metadata["peer_id"]),
            parent_external_id=str(index - 1) if index % 3 == 0 else "",
            thread_url=f"https://t.me/demo_transport/{index}" if channel == ChannelMessage.Channel.TELEGRAM else "",
            sentiment=ticket.sentiment,
            ticket=ticket,
            company=ticket.company,
        )
        return message

    def _create_response(self, ticket, message, operator, index, base_time):
        response = TicketResponse.objects.create(
            ticket=ticket,
            channel_message=message,
            author=operator,
            channel=TicketResponse.Channel.VK
            if message.channel == ChannelMessage.Channel.VK
            else TicketResponse.Channel.TELEGRAM,
            body=self._response_text(ticket),
            status=TicketResponse.Status.SENT,
            external_message_id=f"demo-response-{index}",
            sent_at=base_time + timedelta(minutes=7),
        )
        TicketResponse.objects.filter(pk=response.pk).update(
            created_at=base_time + timedelta(minutes=5)
        )
        return response

    def _response_text(self, ticket):
        if ticket.category == Ticket.Category.PRAISE:
            return "Спасибо за обратную связь. Передали благодарность команде смены."
        if ticket.category == Ticket.Category.INCIDENT:
            return "Информация передана дежурной смене и службе безопасности. Проверка уже начата."
        if ticket.category == Ticket.Category.PAYMENT:
            return "Проверим операцию оплаты и вернемся с результатом по обращению."
        return "Спасибо, обращение принято в работу. Ответственный специалист уже назначен."
