import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-integrations',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
  ],
  templateUrl: './integrations.component.html',
  styleUrls: ['./integrations.component.css'],
})
export class IntegrationsComponent {
}

