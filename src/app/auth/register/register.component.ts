import { Component, inject } from '@angular/core';
import {
  FormBuilder, ReactiveFormsModule, Validators, AbstractControl, ValidationErrors
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthApiService } from '../../services/auth-api.service';
import { AuthService } from '../../core/services/auth.service';
import { TokenService } from '../../core/services/token.service';
import { NotificationService } from '../../core/services/notification.service';

function passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
  const pw = control.get('password')?.value;
  const confirm = control.get('confirmPassword')?.value;
  return pw && confirm && pw !== confirm ? { passwordMismatch: true } : null;
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [
    ReactiveFormsModule, RouterLink,
    MatFormFieldModule, MatInputModule, MatButtonModule,
    MatIconModule, MatSelectModule, MatProgressSpinnerModule,
  ],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss',
})
export class RegisterComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authApi = inject(AuthApiService);
  private readonly authService = inject(AuthService);
  private readonly tokenService = inject(TokenService);
  private readonly notification = inject(NotificationService);
  private readonly router = inject(Router);

  loading = false;
  hidePassword = true;
  hideConfirm = true;

  form = this.fb.group({
    full_name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    role: ['teacher', Validators.required],
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', Validators.required],
  }, { validators: passwordMatchValidator });

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading = true;
    const { full_name, email, role, password } = this.form.getRawValue() as {
      full_name: string; email: string; role: 'admin' | 'teacher'; password: string;
    };
    this.authApi.register({ full_name, email, role, password }).subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success && res.data) {
          this.tokenService.setTokens(res.data.access_token, res.data.refresh_token);
          this.authApi.getMe().subscribe({
            next: (meRes) => {
              if (meRes.success && meRes.data) this.authService.setUser(meRes.data);
              this.router.navigate(['/dashboard']);
            },
            error: () => this.router.navigate(['/dashboard']),
          });
          this.notification.success('Account created! Welcome aboard.');
        }
      },
      error: () => { this.loading = false; },
    });
  }
}
