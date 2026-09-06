import { AuthService } from "../services/authService";

export class AuthController {
  private service: AuthService;

  constructor(service: AuthService) {
    this.service = service;
  }

  login(credentials: object): object {
    console.log("login attempt", credentials);
    return this.service.login(credentials);
  }

  logout(sessionId: string): object {
    return this.service.logout(sessionId);
  }
}
