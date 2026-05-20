import { Component, Input } from '@angular/core';
import { Location } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-page-header',
  standalone: true,
  imports: [MatButtonModule, MatIconModule],
  template: `
    <div class="page-header">
      @if (showBack) {
        <button mat-icon-button (click)="goBack()" class="back-btn" aria-label="Go back">
          <mat-icon>arrow_back</mat-icon>
        </button>
      }
      <div class="header-text">
        <h1 class="page-title">{{ title }}</h1>
        @if (subtitle) {
          <p class="page-subtitle">{{ subtitle }}</p>
        }
      </div>
      <div class="header-actions">
        <ng-content />
      </div>
    </div>
  `,
  styles: [`
    .page-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 24px;
    }
    .back-btn { flex-shrink: 0; }
    .header-text { flex: 1; }
    .page-title { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .page-subtitle { margin: 2px 0 0; font-size: 0.875rem; color: #64748b; }
    .header-actions { display: flex; gap: 8px; align-items: center; }
  `]
})
export class PageHeaderComponent {
  @Input() title = '';
  @Input() subtitle = '';
  @Input() showBack = false;

  constructor(private location: Location) {}

  goBack(): void { this.location.back(); }
}
