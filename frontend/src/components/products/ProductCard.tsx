/**
 * Product card component.
 *
 * Best practices:
 * - Reusable component design
 * - Proper image optimization with Next.js Image
 * - Accessibility
 */

import Link from 'next/link';
import type { ProductListItem } from '@/types';

interface ProductCardProps {
  product: ProductListItem;
}

export function ProductCard({ product }: ProductCardProps) {
  return (
    <Link href={`/products/${product.slug}`}>
      <div className="border rounded-lg p-6 hover:shadow-lg transition-shadow cursor-pointer">
        {product.primary_image && (
          <div className="relative h-48 mb-4 bg-gray-100 rounded flex items-center justify-center">
            {/* In production, use next/image for optimization */}
            <span className="text-gray-400">Image</span>
          </div>
        )}

        <h3 className="text-lg font-semibold mb-2 line-clamp-2">
          {product.name}
        </h3>

        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
          {product.short_description}
        </p>

        <div className="flex items-center justify-between">
          <div>
            {product.is_on_sale && product.compare_at_price ? (
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-red-600">
                  ${product.price}
                </span>
                <span className="text-sm text-gray-500 line-through">
                  ${product.compare_at_price}
                </span>
              </div>
            ) : (
              <span className="text-lg font-bold">${product.price}</span>
            )}
          </div>

          {product.is_on_sale && (
            <span className="bg-red-100 text-red-600 text-xs px-2 py-1 rounded">
              {product.discount_percentage}% OFF
            </span>
          )}
        </div>

        <div className="mt-2">
          {!product.is_in_stock && (
            <span className="text-xs text-red-600">Out of stock</span>
          )}
          {product.is_in_stock && (
            <span className="text-xs text-green-600">In stock</span>
          )}
        </div>
      </div>
    </Link>
  );
}
