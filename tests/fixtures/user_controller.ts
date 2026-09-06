import { UserService } from "../services/userService";
import * as express from "express";

export function healthCheck(): object {
  return { status: "ok" };
}

export class UserController {
  private service: UserService;

  constructor(service: UserService) {
    this.service = service;
  }

  getUser(id: string): object | null {
    return this.service.findById(id);
  }

  createUser(payload: object): object {
    return this.service.create(payload);
  }
}
