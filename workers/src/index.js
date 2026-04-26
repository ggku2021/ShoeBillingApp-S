import { Router } from 'itty-router';
import { handle as productsHandle } from './routes/products.js';
import { handle as quotesHandle } from './routes/quotes.js';
import { handle as ordersHandle } from './routes/orders.js';

const router = Router();

// Health check
router.get('/api/health', () => new Response('OK', { status: 200 }));

// Product routes
router.get('/api/products', productsHandle);
router.post('/api/products', productsHandle);
router.get('/api/products/:id', productsHandle);
router.put('/api/products/:id', productsHandle);
router.delete('/api/products/:id', productsHandle);

// Quote routes
router.get('/api/quotes', quotesHandle);
router.post('/api/quotes', quotesHandle);
router.get('/api/quotes/:id', quotesHandle);
router.put('/api/quotes/:id', quotesHandle);
router.delete('/api/quotes/:id', quotesHandle);

// Order routes
router.get('/api/orders', ordersHandle);
router.post('/api/orders', ordersHandle);
router.get('/api/orders/:id', ordersHandle);
router.put('/api/orders/:id', ordersHandle);
router.delete('/api/orders/:id', ordersHandle);

// 404
router.all('*', () => new Response('Not Found', { status: 404 }));

export default {
  fetch: (request, env) => {
    // Bind env to global for convenience (DB, R2_BUCKET)
    globalThis.DB = env.DB;
    globalThis.R2_BUCKET = env.R2_BUCKET;
    return router.handle(request).catch(err => {
      console.error(err);
      return new Response('Internal Error', { status: 500 });
    });
  }
};