/*
  Contrato público de la feature products (F5). Lo de afuera SOLO importa desde aquí.
*/
export { CategoryList } from './components/CategoryList'
export { ProductList } from './components/ProductList'
export { UnitList } from './components/UnitList'
export { useCategories } from './hooks/useCategories'
export { useProducts } from './hooks/useProducts'
export { useUnits } from './hooks/useUnits'
export type {
  Category,
  CategoryWriteInput,
  Product,
  ProductWriteInput,
  UnitOfMeasure,
  UnitOfMeasureWriteInput,
} from './types/products.types'
