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
    must_change_password: z.boolean(),
  })
  .passthrough();
const TokenResponse = z
  .object({ access: z.string(), user: UserIdentity })
  .passthrough();
const AccessToken = z.object({ access: z.string() }).passthrough();
const UserAdminRead = z
  .object({
    id: z.number().int(),
    username: z.string(),
    first_name: z.string(),
    last_name: z.string(),
    role: RoleEnum,
    is_active: z.boolean(),
    profile: ProfileRead.nullable(),
    must_change_password: z.boolean(),
  })
  .passthrough();
const UserAdminWrite = z
  .object({
    username: z
      .string()
      .max(150)
      .regex(/^[\w.@+-]+$/),
    password: z.string(),
    profile_id: z.string().uuid(),
    first_name: z.string().max(150).optional(),
    last_name: z.string().max(150).optional(),
  })
  .passthrough();
const PatchedUserAdminUpdate = z
  .object({ first_name: z.string().max(150), last_name: z.string().max(150) })
  .partial()
  .passthrough();
const ResetPasswordWrite = z
  .object({
    temporary_password: z.string(),
    generate: z.boolean().default(false),
  })
  .partial()
  .passthrough();
const ResetPasswordRead = z
  .object({ temporary_password: z.string() })
  .passthrough();
const ProfileWrite = z
  .object({
    name: z.string().max(100),
    description: z.string().max(255).optional(),
    permissions: z.record(z.string(), z.array(z.string())).optional(),
    visible_sensitive_fields: z.array(z.string()).optional(),
    auto_approval: z.boolean().optional(),
  })
  .passthrough();
const PatchedProfileAdminWrite = z
  .object({
    description: z.string().max(255),
    permissions: z.record(z.string(), z.array(z.string())),
    visible_sensitive_fields: z.array(z.string()),
    auto_approval: z.boolean(),
  })
  .partial()
  .passthrough();
const AssignProfile = z.object({ profile_id: z.string().uuid() }).passthrough();
const FacetEnum = z.enum(["CLIENTE", "PROVEEDOR"]);
const CreditTermsWrite = z
  .object({
    ficha: z.string().uuid(),
    facet: FacetEnum,
    credit_limit: z.string().regex(/^-?\d{0,10}(?:\.\d{0,2})?$/),
    term_days: z.number().int().gte(0).lte(2147483647).optional(),
    notice_days: z.number().int().gte(0).lte(2147483647).optional(),
  })
  .passthrough();
const CreditTermsRead = z
  .object({
    id: z.string().uuid(),
    ficha: z.string().uuid(),
    facet: FacetEnum,
    credit_limit: z.string().regex(/^-?\d{0,10}(?:\.\d{0,2})?$/),
    term_days: z.number().int(),
    notice_days: z.number().int(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const PatchedCreditTermsWrite = z
  .object({
    ficha: z.string().uuid(),
    facet: FacetEnum,
    credit_limit: z.string().regex(/^-?\d{0,10}(?:\.\d{0,2})?$/),
    term_days: z.number().int().gte(0).lte(2147483647),
    notice_days: z.number().int().gte(0).lte(2147483647),
  })
  .partial()
  .passthrough();
const IdentificationTypeEnum = z.enum(["CEDULA", "RUC", "PASAPORTE"]);
const RolesEnum = z.enum([
  "CLIENTE",
  "PROVEEDOR",
  "RESPONSABLE_RUTA",
  "CHOFER",
]);
const StatusEnum = z.enum(["ACTIVO", "BLOQUEADO", "INACTIVO"]);
const FichaRead = z
  .object({
    id: z.string().uuid(),
    name: z.string(),
    identification_type: IdentificationTypeEnum,
    identification_number: z.string(),
    email: z.string().email(),
    phone: z.string(),
    roles: z.array(RolesEnum),
    status: StatusEnum,
    user: z.number().int().nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const FichaWrite = z
  .object({
    name: z.string().max(255),
    identification_type: IdentificationTypeEnum,
    identification_number: z.string().max(20),
    email: z.string().max(254).email().optional(),
    phone: z.string().max(20).optional(),
    roles: z.array(RolesEnum),
  })
  .passthrough();
const PatchedFichaWrite = z
  .object({
    name: z.string().max(255),
    identification_type: IdentificationTypeEnum,
    identification_number: z.string().max(20),
    email: z.string().max(254).email(),
    phone: z.string().max(20),
    roles: z.array(RolesEnum),
  })
  .partial()
  .passthrough();
const LinkUserWrite = z.object({ user: z.number().int() }).passthrough();

export const schemas = {
  ChangePassword,
  Detail,
  Login,
  RoleEnum,
  ProfileRead,
  UserIdentity,
  TokenResponse,
  AccessToken,
  UserAdminRead,
  UserAdminWrite,
  PatchedUserAdminUpdate,
  ResetPasswordWrite,
  ResetPasswordRead,
  ProfileWrite,
  PatchedProfileAdminWrite,
  AssignProfile,
  FacetEnum,
  CreditTermsWrite,
  CreditTermsRead,
  PatchedCreditTermsWrite,
  IdentificationTypeEnum,
  RolesEnum,
  StatusEnum,
  FichaRead,
  FichaWrite,
  PatchedFichaWrite,
  LinkUserWrite,
};
