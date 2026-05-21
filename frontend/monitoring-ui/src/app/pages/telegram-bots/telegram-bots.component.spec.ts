import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

import { TelegramBotsComponent } from './telegram-bots.component';
import { TelegramBotService } from '../../services/telegram-bot.service';
import { AuthService } from '../../services/auth.service';

describe('TelegramBotsComponent', () => {
  let fixture: ComponentFixture<TelegramBotsComponent>;
  let component: TelegramBotsComponent;
  let botService: jasmine.SpyObj<TelegramBotService>;

  beforeEach(async () => {
    botService = jasmine.createSpyObj<TelegramBotService>('TelegramBotService', [
      'getBots',
      'createBot',
      'updateBot',
      'deleteBot',
    ]);
    botService.getBots.and.returnValue(of([]));
    botService.createBot.and.returnValue(of({
      id: 1,
      bot_token: 'token',
      bot_username: 'transport_bot',
      chat_ids: ['-1001'],
      discussion_chat_ids: ['-1002'],
      allow_direct: true,
      status: 'active',
    }));

    await TestBed.configureTestingModule({
      imports: [TelegramBotsComponent, NoopAnimationsModule],
      providers: [
        { provide: TelegramBotService, useValue: botService },
        {
          provide: AuthService,
          useValue: {
            isCompanyAdmin: () => true,
            isSuperAdmin: () => false,
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TelegramBotsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('sends direct messages and group chat ids from the UI form', () => {
    component.botToken = '123456:valid-token';
    component.allowDirect = true;
    component.chatIdsText = '-1001, -1002\n-1003';
    component.discussionChatIdsText = '-2001';

    component.onSubmit();

    expect(botService.createBot).toHaveBeenCalledWith({
      bot_token: '123456:valid-token',
      chat_ids: ['-1001', '-1002', '-1003'],
      discussion_chat_ids: ['-2001'],
      allow_direct: true,
    });
  });
});
