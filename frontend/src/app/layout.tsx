/**
 * Root layout with providers.
 *
 * Best practices:
 * - Wrap app with providers at root level
 * - Configure metadata for SEO
 * - Load global styles
 */

import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: {
    template: '%s | MyApp',
    default: 'MyApp - E-Commerce Platform',
  },
  description: 'Full-stack e-commerce platform built with Django and Next.js',
  keywords: ['e-commerce', 'django', 'nextjs', 'react'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
