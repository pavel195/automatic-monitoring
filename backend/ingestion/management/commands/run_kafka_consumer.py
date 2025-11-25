from django.core.management.base import BaseCommand

from ingestion.consumers import RawMessageConsumer


class Command(BaseCommand):
    help = "Запускает Kafka consumer для обработки входящих сообщений"

    def handle(self, *args, **options):
        consumer = RawMessageConsumer()
        self.stdout.write(self.style.SUCCESS("Kafka consumer запущен"))
        consumer.run_forever()

