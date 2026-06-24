import { z } from "zod";

const ChangePassword = z
  .object({ current_password: z.string(), new_password: z.string() })
  .passthrough();
const Detail = z.object({ detail: z.string() }).passthrough();
const Login = z
  .object({ username: z.string(), password: z.string() })
  .passthrough();
const RoleEnum = z.enum(["JEFE", "SUPERVISOR", "RUTA", "USUARIO"]);
const UserIdentity = z
  .object({
    id: z.number().int(),
    username: z.string(),
    first_name: z.string(),
    last_name: z.string(),
    role: RoleEnum,
    is_active: z.boolean(),
  })
  .passthrough();
const TokenResponse = z
  .object({ access: z.string(), user: UserIdentity })
  .passthrough();
const AccessToken = z.object({ access: z.string() }).passthrough();

export const schemas = {
  ChangePassword,
  Detail,
  Login,
  RoleEnum,
  UserIdentity,
  TokenResponse,
  AccessToken,
};
