import { SessionService } from "../services/sessionService";

export class SessionController {
  private service: SessionService;

  constructor(service: SessionService) {
    this.service = service;
  }

  getSession(sessionId: string): object {
    return this.service.findById(sessionId);
  }

  refreshSession(sessionId: string): object {
    return this.service.refresh(sessionId);
  }
}
