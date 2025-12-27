/**
 * Product list component.
 *
 * Best practices:
 * - Use React Query for server state
 * - Handle loading and error states
 * - Implement proper TypeScript types
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api';
import type { PaginatedResponse, ProductListItem } from '@/types';
import { ProductCard } from './ProductCard';

export function ProductList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['products'],
    queryFn: () =>
      apiClient.get<PaginatedResponse<ProductListItem>>('/api/v1/products/'),
  });

  if (isLoading) {
    return (
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="border rounded-lg p-6 animate-pulse">
            <div className="h-48 bg-gray-200 rounded mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Error loading products</p>
        <p className="text-gray-500 text-sm mt-2">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    );
  }

  if (!data || data.results.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No products found</p>
      </div>
    );
  }

  return (
    <div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {data.results.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>

      {data.count > data.results.length && (
        <div className="mt-8 text-center">
          <p className="text-gray-500">
            Showing {data.results.length} of {data.count} products
          </p>
        </div>
      )}
    </div>
  );
}
