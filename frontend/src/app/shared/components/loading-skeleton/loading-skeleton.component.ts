import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-loading-skeleton',
  standalone: true,
  template: `
    <div class="skeleton-wrapper">
      @for (row of rows; track $index) {
        <div class="skeleton-row" [style.width]="row + '%'"></div>
      }
    </div>
  `,
  styles: [`
    .skeleton-wrapper {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 8px 0;
    }
    .skeleton-row {
      height: var(--sk-height, 16px);
      background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
      background-size: 200% 100%;
      border-radius: 4px;
      animation: shimmer 1.4s infinite;
    }
    @keyframes shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `],
})
export class LoadingSkeletonComponent {
  @Input() rows: number[] = [100, 90, 75, 100, 85, 60];
  @Input() height = '16px';
  @Input() count = 0;

  get resolvedRows(): number[] {
    if (this.count > 0) return Array.from({ length: this.count }, () => Math.floor(60 + Math.random() * 40));
    return this.rows;
  }
}
