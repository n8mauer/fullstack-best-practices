/**
 * Products page - demonstrates data fetching and client components.
 *
 * Best practices:
 * - Fetch data on server when possible
 * - Use client components only when needed
 * - Implement proper loading and error states
 */

import { ProductList } from '@/components/products/ProductList';
import { Suspense } from 'react';

export const metadata = {
  title: 'Products',
  description: 'Browse our product catalog',
};

export default function ProductsPage() {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Products</h1>

        <Suspense
          fallback={
            <div className="text-center py-12">
              <p className="text-gray-500">Loading products...</p>
            </div>
          }
        >
          <ProductList />
        </Suspense>
      </div>
    </main>
  );
}
