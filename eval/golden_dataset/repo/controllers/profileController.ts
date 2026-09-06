import { ProfileService } from "../services/profileService";

export class ProfileController {
  private service: ProfileService;

  constructor(service: ProfileService) {
    this.service = service;
  }

  getProfile(userId: string): object {
    return this.service.findById(userId);
  }

  updateBio(userId: string, rawBio: string): object {
    // business logic embedded directly in the controller: sanitizing and
    // enforcing a length limit instead of delegating to the service.
    const trimmed = rawBio.trim();
    if (trimmed.length > 280) {
      throw new Error("Bio exceeds maximum length of 280 characters");
    }
    const sanitized = trimmed.replace(/<[^>]*>/g, "");
    return this.service.updateBio(userId, sanitized);
  }
}
