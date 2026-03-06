import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const publicPaths = [
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
  '/pricing',
  '/auth/callback',
  '/',
];

const authPaths = ['/login', '/register', '/forgot-password', '/reset-password'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get('access_token')?.value;

  // Check if the path is public
  const isPublicPath = publicPaths.some(
    (path) => pathname === path || pathname.startsWith('/api/')
  );

  // Check if the path is an auth path (login, register, etc.)
  const isAuthPath = authPaths.some((path) => pathname === path);

  // If user is logged in and trying to access auth pages, redirect to dashboard
  if (token && isAuthPath) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // If user is not logged in and trying to access protected pages
  if (!token && !isPublicPath) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
