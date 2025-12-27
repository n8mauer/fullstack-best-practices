/**
 * TypeScript type definitions for API models.
 *
 * Best practice: Keep types in sync with backend models.
 * Consider using tools like openapi-typescript for automatic
 * type generation from OpenAPI specs.
 */

// User types
export interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  is_verified: boolean;
  is_active: boolean;
  date_joined: string;
  profile: UserProfile | null;
}

export interface UserProfile {
  bio: string;
  avatar: string | null;
  date_of_birth: string | null;
  address: string;
  city: string;
  country: string;
  postal_code: string;
  newsletter_subscribed: boolean;
  email_notifications: boolean;
}

// Product types
export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string;
  product_count: number;
}

export interface ProductImage {
  id: number;
  image: string;
  alt_text: string;
  is_primary: boolean;
  order: number;
}

export interface Product {
  id: number;
  name: string;
  slug: string;
  sku: string;
  description: string;
  short_description: string;
  price: string;
  compare_at_price: string | null;
  is_on_sale: boolean;
  discount_percentage: number;
  stock_quantity: number;
  is_low_stock: boolean;
  is_in_stock: boolean;
  category: Category;
  images: ProductImage[];
  is_active: boolean;
  is_featured: boolean;
  meta_title: string;
  meta_description: string;
  view_count: number;
  sales_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProductListItem {
  id: number;
  name: string;
  slug: string;
  sku: string;
  short_description: string;
  price: string;
  compare_at_price: string | null;
  is_on_sale: boolean;
  discount_percentage: number;
  category_name: string;
  is_active: boolean;
  is_featured: boolean;
  is_in_stock: boolean;
  primary_image: string | null;
}

// Order types
export interface OrderItem {
  id: number;
  product: number;
  product_details?: ProductListItem;
  product_name: string;
  product_sku: string;
  unit_price: string;
  quantity: number;
  total: string;
}

export interface OrderStatusHistory {
  id: number;
  status: OrderStatus;
  notes: string;
  created_at: string;
}

export enum OrderStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  CONFIRMED = 'confirmed',
  SHIPPED = 'shipped',
  DELIVERED = 'delivered',
  CANCELLED = 'cancelled',
  REFUNDED = 'refunded',
}

export interface Order {
  id: number;
  order_number: string;
  status: OrderStatus;
  user: number;
  subtotal: string;
  tax: string;
  shipping: string;
  total: string;
  shipping_name: string;
  shipping_address: string;
  shipping_city: string;
  shipping_postal_code: string;
  shipping_country: string;
  email: string;
  phone: string;
  customer_notes: string;
  admin_notes: string;
  items: OrderItem[];
  status_history: OrderStatusHistory[];
  created_at: string;
  confirmed_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
}

// Pagination types
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// API error type
export interface APIErrorResponse {
  detail?: string;
  [key: string]: any;
}

// Form types
export interface LoginFormData {
  email: string;
  password: string;
}

export interface RegisterFormData {
  email: string;
  username: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  phone?: string;
}

export interface OrderCreateData {
  items: Array<{
    product_id: number;
    quantity: number;
  }>;
  shipping_name: string;
  shipping_address: string;
  shipping_city: string;
  shipping_postal_code: string;
  shipping_country: string;
  phone: string;
  customer_notes?: string;
}
