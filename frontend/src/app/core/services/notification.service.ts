import { Injectable, inject } from '@angular/core';
import { MatSnackBar, MatSnackBarConfig } from '@angular/material/snack-bar';

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly snackBar = inject(MatSnackBar);

  private show(message: string, panelClass: string, duration = 4000): void {
    const config: MatSnackBarConfig = {
      duration,
      horizontalPosition: 'end',
      verticalPosition: 'top',
      panelClass: [panelClass],
    };
    this.snackBar.open(message, 'Dismiss', config);
  }

  success(message: string): void {
    this.show(message, 'snack-success');
  }

  error(message: string): void {
    this.show(message, 'snack-error', 6000);
  }

  warning(message: string): void {
    this.show(message, 'snack-warning');
  }

  info(message: string): void {
    this.show(message, 'snack-info');
  }
}
