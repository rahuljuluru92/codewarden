import { AdminService } from "../services/adminService";

export class AdminController {
  private service: AdminService;

  constructor(service: AdminService) {
    this.service = service;
  }

  banUser(userId: string, reason: string): object {
    console.log("banning user", userId, reason);
    // business logic embedded directly in the controller: deciding ban
    // duration based on reason text instead of delegating to the service.
    let durationDays = 7;
    if (reason.toLowerCase().includes("severe")) {
      durationDays = 30;
    } else if (reason.toLowerCase().includes("minor")) {
      durationDays = 1;
    }
    return this.service.ban(userId, durationDays);
  }
}
