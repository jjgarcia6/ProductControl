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
    price_list: z.string().uuid().nullable(),
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
const PatchedAssignPriceList = z
  .object({ price_list: z.string().uuid().nullable() })
  .partial()
  .passthrough();
const LinkUserWrite = z.object({ user: z.number().int() }).passthrough();
const PatchedPriceListItemWrite = z
  .object({
    product: z.string().uuid(),
    price: z.string().regex(/^-?\d{0,10}(?:\.\d{0,2})?$/),
  })
  .partial()
  .passthrough();
const PriceListItemRead = z
  .object({
    id: z.string().uuid(),
    price_list: z.string().uuid(),
    product: z.string().uuid(),
    product_name: z.string(),
    price: z.string().regex(/^-?\d{0,10}(?:\.\d{0,2})?$/),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const TypeEnum = z.enum(["NORMAL", "DESCARTE"]);
const PriceListRead = z
  .object({
    id: z.string().uuid(),
    name: z.string(),
    type: TypeEnum,
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const PriceListWrite = z
  .object({ name: z.string().max(120), type: TypeEnum })
  .passthrough();
const PatchedPriceListWrite = z
  .object({ name: z.string().max(120), type: TypeEnum })
  .partial()
  .passthrough();
const PriceListItemWrite = z
  .object({
    product: z.string().uuid(),
    price: z.string().regex(/^-?\d{0,10}(?:\.\d{0,2})?$/),
  })
  .passthrough();
const IntakeTypeEnum = z.enum(["GAVETA", "PESO"]);
const CategoryRead = z
  .object({
    id: z.string().uuid(),
    name: z.string(),
    shelf_life_days: z.number().int(),
    intake_type: IntakeTypeEnum,
    merma_min: z
      .string()
      .regex(/^-?\d{0,9}(?:\.\d{0,3})?$/)
      .nullable(),
    merma_max: z
      .string()
      .regex(/^-?\d{0,9}(?:\.\d{0,3})?$/)
      .nullable(),
    reference_qty: z.string().regex(/^-?\d{0,9}(?:\.\d{0,3})?$/),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const CategoryWrite = z
  .object({
    name: z.string().max(128),
    shelf_life_days: z.number().int().gte(0).lte(2147483647).optional(),
    intake_type: IntakeTypeEnum,
    merma_min: z
      .string()
      .regex(/^-?\d{0,9}(?:\.\d{0,3})?$/)
      .nullish(),
    merma_max: z
      .string()
      .regex(/^-?\d{0,9}(?:\.\d{0,3})?$/)
      .nullish(),
    reference_qty: z
      .string()
      .regex(/^-?\d{0,9}(?:\.\d{0,3})?$/)
      .optional(),
  })
  .passthrough();
const PatchedCategoryWrite = z
  .object({
    name: z.string().max(128),
    shelf_life_days: z.number().int().gte(0).lte(2147483647),
    intake_type: IntakeTypeEnum,
    merma_min: z
      .string()
      .regex(/^-?\d{0,9}(?:\.\d{0,3})?$/)
      .nullable(),
    merma_max: z
      .string()
      .regex(/^-?\d{0,9}(?:\.\d{0,3})?$/)
      .nullable(),
    reference_qty: z.string().regex(/^-?\d{0,9}(?:\.\d{0,3})?$/),
  })
  .partial()
  .passthrough();
const ProductRead = z
  .object({
    id: z.string().uuid(),
    name: z.string(),
    category: z.string().uuid(),
    category_name: z.string(),
    unit_of_measure: z.string().uuid(),
    unit_of_measure_name: z.string(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const ProductWrite = z
  .object({
    name: z.string().max(128),
    category: z.string().uuid(),
    unit_of_measure: z.string().uuid(),
  })
  .passthrough();
const PatchedProductWrite = z
  .object({
    name: z.string().max(128),
    category: z.string().uuid(),
    unit_of_measure: z.string().uuid(),
  })
  .partial()
  .passthrough();
const UnitOfMeasureRead = z
  .object({
    id: z.string().uuid(),
    name: z.string(),
    symbol: z.string(),
    conversion_factor: z.string().regex(/^-?\d{0,6}(?:\.\d{0,6})?$/),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const UnitOfMeasureWrite = z
  .object({
    name: z.string().max(64),
    symbol: z.string().max(16),
    conversion_factor: z.string().regex(/^-?\d{0,6}(?:\.\d{0,6})?$/),
  })
  .passthrough();
const PatchedUnitOfMeasureWrite = z
  .object({
    name: z.string().max(64),
    symbol: z.string().max(16),
    conversion_factor: z.string().regex(/^-?\d{0,6}(?:\.\d{0,6})?$/),
  })
  .partial()
  .passthrough();

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
  PatchedAssignPriceList,
  LinkUserWrite,
  PatchedPriceListItemWrite,
  PriceListItemRead,
  TypeEnum,
  PriceListRead,
  PriceListWrite,
  PatchedPriceListWrite,
  PriceListItemWrite,
  IntakeTypeEnum,
  CategoryRead,
  CategoryWrite,
  PatchedCategoryWrite,
  ProductRead,
  ProductWrite,
  PatchedProductWrite,
  UnitOfMeasureRead,
  UnitOfMeasureWrite,
  PatchedUnitOfMeasureWrite,
};
