export const getDefaultLandingRoute = (user) => {
  if (user?.role === 'admin') {
    return '/logs';
  }

  return '/chat';
};
