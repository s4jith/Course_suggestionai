import { Component, Input } from '@angular/core';
import { TopicStatus } from '../../../models/lesson-plan.model';

const STATUS_CONFIG: Record<TopicStatus, { label: string; bg: string; color: string; dot: string }> = {
  pending:     { label: 'Pending',     bg: '#f1f5f9', color: '#475569', dot: '#94a3b8' },
  in_progress: { label: 'In Progress', bg: '#dbeafe', color: '#1d4ed8', dot: '#2563eb' },
  completed:   { label: 'Completed',   bg: '#dcfce7', color: '#166534', dot: '#16a34a' },
  skipped:     { label: 'Skipped',     bg: '#fee2e2', color: '#991b1b', dot: '#dc2626' },
};

@Component({
  selector: 'app-topic-status-chip',
  standalone: true,
  template: `
    <span class="status-chip" [style.background]="cfg.bg" [style.color]="cfg.color">
      <span class="dot" [style.background]="cfg.dot"></span>
      {{ cfg.label }}
    </span>
  `,
  styles: [`
    .status-chip {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 9px;
      border-radius: 12px;
      font-size: 0.72rem;
      font-weight: 600;
      white-space: nowrap;
      letter-spacing: 0.02em;
    }
    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      flex-shrink: 0;
    }
  `],
})
export class TopicStatusChipComponent {
  @Input() set status(s: TopicStatus) { this.cfg = STATUS_CONFIG[s] ?? STATUS_CONFIG['pending']; }

  cfg = STATUS_CONFIG['pending'];
}
