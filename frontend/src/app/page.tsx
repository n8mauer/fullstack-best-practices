/**
 * Home page - Server Component by default.
 *
 * Best practices:
 * - Use Server Components for static content
 * - Fetch data at the component level
 * - Implement proper error handling
 */

import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-6">
          Full-Stack Best Practices Example
        </h1>

        <p className="text-lg mb-8 text-gray-600">
          This is a comprehensive example demonstrating best practices for
          building production-ready applications with Django, PostgreSQL, Redis,
          Celery, AmazonMQ, and Next.js.
        </p>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="border rounded-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">Backend</h2>
            <ul className="space-y-2 text-gray-600">
              <li>✓ Django 5.0 with PostgreSQL</li>
              <li>✓ Redis for caching</li>
              <li>✓ Celery + AmazonMQ for async tasks</li>
              <li>✓ Django REST Framework</li>
              <li>✓ JWT Authentication</li>
              <li>✓ Proper error handling</li>
            </ul>
          </div>

          <div className="border rounded-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">Frontend</h2>
            <ul className="space-y-2 text-gray-600">
              <li>✓ Next.js 14 App Router</li>
              <li>✓ TypeScript for type safety</li>
              <li>✓ React Query for server state</li>
              <li>✓ Tailwind CSS for styling</li>
              <li>✓ Form validation with Zod</li>
              <li>✓ API client abstraction</li>
            </ul>
          </div>
        </div>

        <div className="mt-8 space-x-4">
          <Link
            href="/products"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
          >
            View Products
          </Link>
          <Link
            href="/login"
            className="inline-block border border-blue-600 text-blue-600 px-6 py-3 rounded-lg hover:bg-blue-50"
          >
            Login
          </Link>
        </div>

        <div className="mt-12 p-6 bg-gray-50 rounded-lg">
          <h3 className="text-xl font-semibold mb-4">Key Features</h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div>
              <h4 className="font-semibold mb-2">Security</h4>
              <p className="text-gray-600">
                JWT authentication, CORS configuration, rate limiting
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Performance</h4>
              <p className="text-gray-600">
                Redis caching, query optimization, server components
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Scalability</h4>
              <p className="text-gray-600">
                Async task processing, connection pooling, load balancing
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
