import { Component, Input } from '@angular/core';
import { DecimalPipe } from '@angular/common';

@Component({
  selector: 'app-progress-ring',
  standalone: true,
  template: `
    <svg [attr.width]="size" [attr.height]="size" viewBox="0 0 36 36" class="ring">
      <circle class="track" cx="18" cy="18" r="15.9" />
      <circle
        class="fill"
        cx="18" cy="18" r="15.9"
        [attr.stroke]="color"
        [attr.stroke-dasharray]="dashArray"
        stroke-dashoffset="25"
      />
      <text x="18" y="20.35" class="label">{{ value | number:'1.0-0' }}%</text>
    </svg>
  `,
  styles: [`
    .ring { transform: rotate(-90deg); overflow: visible; }
    .track {
      fill: none;
      stroke: #e2e8f0;
      stroke-width: 3.5;
    }
    .fill {
      fill: none;
      stroke-width: 3.5;
      stroke-linecap: round;
      transition: stroke-dasharray 0.5s ease;
    }
    .label {
      fill: #1e293b;
      font-size: 8px;
      font-weight: 700;
      text-anchor: middle;
      transform: rotate(90deg);
      transform-origin: 18px 18px;
    }
  `],
  imports: [DecimalPipe],
})
export class ProgressRingComponent {
  @Input() value = 0;
  @Input() size = 80;
  @Input() color = '#4f46e5';

  get dashArray(): string {
    const pct = Math.min(100, Math.max(0, this.value));
    const circumference = 100;
    return `${pct} ${circumference - pct}`;
  }
}
