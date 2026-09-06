import { AuthController } from "../controllers/authController";

export class EmailService {
  private authController: AuthController;

  constructor(authController: AuthController) {
    // deliberately-planted violation: a service importing from the
    // controller layer.
    this.authController = authController;
  }

  sendWelcomeEmail(to: string): boolean {
    return true;
  }
}
