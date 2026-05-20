import { Component, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-stat-card',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div class="stat-card" [style.--accent-color]="color">
      <div class="stat-icon">
        <mat-icon>{{ icon }}</mat-icon>
      </div>
      <div class="stat-info">
        <div class="stat-value">{{ value }}</div>
        <div class="stat-title">{{ title }}</div>
        @if (subtitle) {
          <div class="stat-subtitle">{{ subtitle }}</div>
        }
      </div>
    </div>
  `,
  styles: [`
    .stat-card {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 20px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      border-left: 4px solid var(--accent-color, #4f46e5);
    }
    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: color-mix(in srgb, var(--accent-color, #4f46e5) 15%, white);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      mat-icon { color: var(--accent-color, #4f46e5); font-size: 24px; }
    }
    .stat-value { font-size: 2rem; font-weight: 700; line-height: 1; color: #1e293b; }
    .stat-title  { font-size: 0.85rem; color: #64748b; margin-top: 2px; font-weight: 500; }
    .stat-subtitle { font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }
  `]
})
export class StatCardComponent {
  @Input() title = '';
  @Input() value: string | number = '';
  @Input() icon = 'info';
  @Input() color = '#4f46e5';
  @Input() subtitle = '';
}
