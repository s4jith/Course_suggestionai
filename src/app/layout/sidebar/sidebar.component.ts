import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AsyncPipe, TitleCasePipe } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { AuthService } from '../../core/services/auth.service';

interface NavItem {
  label: string;
  icon: string;
  route: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, AsyncPipe, TitleCasePipe, MatListModule, MatIconModule, MatDividerModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {
  protected readonly authService = inject(AuthService);

  readonly navItems: NavItem[] = [
    { label: 'Dashboard',         icon: 'dashboard',          route: '/dashboard' },
    { label: 'Subjects',          icon: 'menu_book',          route: '/subjects' },
    { label: 'Lesson Plans',      icon: 'assignment',         route: '/lesson-plans' },
    { label: 'AI Recommendations',icon: 'auto_awesome',       route: '/ai' },
  ];
}
