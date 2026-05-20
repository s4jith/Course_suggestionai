import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { noAuthGuard } from './core/guards/no-auth.guard';
import { AppLayoutComponent } from './layout/app-layout/app-layout.component';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },

  {
    path: 'auth/login',
    loadComponent: () => import('./auth/login/login.component').then(m => m.LoginComponent),
    canActivate: [noAuthGuard],
  },
  {
    path: 'auth/register',
    loadComponent: () => import('./auth/register/register.component').then(m => m.RegisterComponent),
    canActivate: [noAuthGuard],
  },

  {
    path: '',
    component: AppLayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: 'dashboard',
        loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent),
      },
      {
        path: 'subjects',
        loadComponent: () => import('./lesson-plan/subject-list/subject-list.component').then(m => m.SubjectListComponent),
      },
      {
        path: 'lesson-plans',
        loadComponent: () => import('./lesson-plan/lesson-plan-list/lesson-plan-list.component').then(m => m.LessonPlanListComponent),
      },
      {
        path: 'lesson-plans/:id',
        loadComponent: () => import('./lesson-plan/lesson-plan-detail/lesson-plan-detail.component').then(m => m.LessonPlanDetailComponent),
      },
      {
        path: 'ai',
        loadComponent: () => import('./ai-recommendations/ai-dashboard/ai-dashboard.component').then(m => m.AiDashboardComponent),
      },
    ],
  },

  { path: '**', redirectTo: '/dashboard' },
];
