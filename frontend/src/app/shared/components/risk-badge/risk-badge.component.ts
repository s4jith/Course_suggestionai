import { Component, Input } from '@angular/core';
import { MatChipsModule } from '@angular/material/chips';
import { RiskLevel } from '../../../models/ai.model';
import { TitleCasePipe } from '@angular/common';

@Component({
  selector: 'app-risk-badge',
  standalone: true,
  imports: [MatChipsModule, TitleCasePipe],
  template: `
    <span class="risk-badge risk-{{ level }}">{{ level | titlecase }}</span>
  `,
  styles: [`
    .risk-badge {
      display: inline-block;
      padding: 3px 10px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .risk-low      { background: #dcfce7; color: #166534; }
    .risk-medium   { background: #fef9c3; color: #854d0e; }
    .risk-high     { background: #ffedd5; color: #9a3412; }
    .risk-critical { background: #fee2e2; color: #991b1b; }
  `]
})
export class RiskBadgeComponent {
  @Input() level: RiskLevel = 'low';
}
