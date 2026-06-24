import { z } from "zod";

const ChangePassword = z
  .object({ current_password: z.string(), new_password: z.string() })
  .passthrough();
const Detail = z.object({ detail: z.string() }).passthrough();
const Login = z
  .object({ username: z.string(), password: z.string() })
  .passthrough();
const RoleEnum = z.enum(["JEFE", "SUPERVISOR", "RUTA", "USUARIO"]);
const ProfileRead = z
  .object({
    id: z.string().uuid(),
    name: z.string(),
    description: z.string(),
    permissions: z.record(z.string(), z.array(z.string())),
    visible_sensitive_fields: z.array(z.string()),
    auto_approval: z.boolean(),
  })
  .passthrough();
const UserIdentity = z
  .object({
    id: z.number().int(),
    username: z.string(),
    first_name: z.string(),
    last_name: z.string(),
    role: RoleEnum,
    is_active: z.boolean(),
    profile: ProfileRead.nullable(),
  })
  .passthrough();
const TokenResponse = z
  .object({ access: z.string(), user: UserIdentity })
  .passthrough();
const AccessToken = z.object({ access: z.string() }).passthrough();
const ProfileWrite = z
  .object({
    name: z.string().max(100),
    description: z.string().max(255).optional(),
    permissions: z.record(z.string(), z.array(z.string())).optional(),
    visible_sensitive_fields: z.array(z.string()).optional(),
    auto_approval: z.boolean().optional(),
  })
  .passthrough();
const AssignProfile = z.object({ profile_id: z.string().uuid() }).passthrough();

export const schemas = {
  ChangePassword,
  Detail,
  Login,
  RoleEnum,
  ProfileRead,
  UserIdentity,
  TokenResponse,
  AccessToken,
  ProfileWrite,
  AssignProfile,
};
