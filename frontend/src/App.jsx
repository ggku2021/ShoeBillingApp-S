import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Link, useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import "./App.css";

const API = import.meta.env.VITE_API_BASE || "http://localhost:8787/api";

const authHeader = {
  Authorization: "Bearer demo-token-shoe-quote",
};

function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/quotes" element={<QuotesPage />} />
          <Route path="/quotes/:id" element={<QuoteEditPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/orders/:id" element={<OrderEditPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

function Navbar() {
  return (
    <nav className="bg-indigo-700 text-white px-4 py-3 shadow-md">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <Link to="/" className="text-xl font-bold">ShoeQuote</Link>
        <div className="flex gap-4 text-sm">
          <Link to="/products" className="hover:underline">Products</Link>
          <Link to="/quotes" className="hover:underline">Quotes</Link>
          <Link to="/orders" className="hover:underline">Orders</Link>
        </div>
      </div>
    </nav>
  );
}

function Home() {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-4">Welcome to Shoe Quotation System</h1>
      <p className="text-gray-600 mb-6">Manage products, create quotes, and track sales orders.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="border rounded p-4 bg-white shadow">
          <h3 className="font-bold text-lg mb-2">Products</h3>
          <p className="text-sm text-gray-600 mb-3">Add and manage your product catalog.</p>
          <Link to="/products" className="text-indigo-600 hover:underline text-sm">Manage →</Link>
        </div>
        <div className="border rounded p-4 bg-white shadow">
          <h3 className="font-bold text-lg mb-2">Quotations</h3>
          <p className="text-sm text-gray-600 mb-3">Create and send price quotes to clients.</p>
          <Link to="/quotes" className="text-indigo-600 hover:underline text-sm">Manage →</Link>
        </div>
        <div className="border rounded p-4 bg-white shadow">
          <h3 className="font-bold text-lg mb-2">Orders</h3>
          <p className="text-sm text-gray-600 mb-3">Track sales orders and shipping status.</p>
          <Link to="/orders" className="text-indigo-600 hover:underline text-sm">Manage →</Link>
        </div>
      </div>
    </div>
  );
}

// ========== PRODUCTS ==========
function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editProduct, setEditProduct] = useState(null);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/products`, { headers: authHeader });
      const data = await res.json();
      setProducts(data.items || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchProducts(); }, []);

  async function deleteProduct(id) {
    if (!confirm("Delete this product?")) return;
    await fetch(`${API}/products/${id}`, { method: "DELETE", headers: authHeader });
    fetchProducts();
  }

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Products</h2>
        <button onClick={() => { setEditProduct(null); setShowModal(true); }}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >+ New Product</button>
      </div>
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {products.map(p => (
            <div key={p.id} className="border rounded p-4 bg-white shadow hover:shadow-md">
              {p.image ? (
                <img src={p.image} alt={p.name} className="w-full h-32 object-cover rounded mb-2" />
              ) : (
                <div className="w-full h-32 bg-gray-100 rounded mb-2 flex items-center justify-center text-gray-400">No Image</div>
              )}
              <h3 className="font-bold text-lg">{p.name}</h3>
              <p className="text-sm text-gray-500">{p.description}</p>
              <div className="mt-2 text-red-600 font-medium">${p.price}</div>
              <div className="mt-2 text-xs text-gray-400">Size: {p.size || "—"} | {p.category || "—"}</div>
              <div className="flex gap-2 mt-3">
                <button onClick={() => { setEditProduct(p); setShowModal(true); }}
                  className="flex-1 bg-blue-500 text-white py-1 rounded text-sm hover:bg-blue-600">Edit</button>
                <button onClick={() => deleteProduct(p.id)}
                  className="flex-1 bg-red-500 text-white py-1 rounded text-sm hover:bg-red-600">Del</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {showModal && <ProductModal product={editProduct} onClose={() => setShowModal(false)} onSave={fetchProducts} />}
    </div>
 );
}

function ProductModal({ product, onClose, onSave }) {
  const { register, handleSubmit, reset } = useForm({
    defaultValues: product || { name: "", description: "", price: 0, category: "", size: "", unit: "pair" }
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (product) reset(product); }, [product, reset]);

  const onSubmit = async (data) => {
    setSaving(true);
    const url = product ? `${API}/products/${product.id}` : `${API}/products`;
    const method = product ? "PUT" : "POST";
    await fetch(url, {
      method,
      headers: { "Content-Type": "application/json", ...authHeader },
      body: JSON.stringify(data)
    });
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
      <div className="bg-white rounded p-6 w-full max-w-md">
        <h3 className="text-lg font-bold mb-4">{product ? "Edit Product" : "New Product"}</h3>
        <form onSubmit={handleSubmit(onSubmit)}>
          <label className="block text-sm mb-1">Name</label>
          <input {...register("name")} className="border w-full px-3 py-2 rounded mb-2" />

          <label className="block text-sm mb-1">Description</label>
          <textarea {...register("description")} rows={3} className="border w-full px-3 py-2 rounded mb-2" />

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-sm mb-1">Category</label>
              <input {...register("category")} className="border w-full px-3 py-2 rounded" />
            </div>
            <div>
              <label className="block text-sm mb-1">Size</label>
              <input {...register("size")} className="border w-full px-3 py-2 rounded" />
            </div>
          </div>

          <label className="block text-sm mb-1 mt-2">Price (USD)</label>
          <input {...register("price")} type="number" step="0.01" className="border w-full px-3 py-2 rounded mb-3" />

          <div className="flex gap-2 mt-4">
            <button type="button" onClick={onClose} className="flex-1 border px-4 py-2 rounded hover:bg-gray-50" disabled={saving}>Cancel</button>
            <button type="submit" className="flex-1 bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ========== QUOTES ==========
function QuotesPage() {
  const navigate = useNavigate();
  const [quotes, setQuotes] = useState([]);

  const fetchQuotes = async () => {
    try {
      const res = await fetch(`${API}/quotes`, { headers: authHeader });
      const data = await res.json();
      setQuotes(data.items || []);
    } catch (e) { console.error(e); }
  };
  useEffect(() => { fetchQuotes(); }, []);

  async function remove(id) {
    if (!confirm("Delete?")) return;
    await fetch(`${API}/quotes/${id}`, { method: "DELETE", headers: authHeader });
    fetchQuotes();
  }

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Quotations</h2>
        <button onClick={() => navigate("/quotes/new")}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">+ New Quote</button>
      </div>
      <div className="bg-white rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="text-left px-4 py-2 font-semibold">Client</th>
              <th className="text-left px-4 py-2 font-semibold">Items</th>
              <th className="text-left px-4 py-2 font-semibold">Total</th>
              <th className="text-left px-4 py-2 font-semibold">Status</th>
              <th className="text-left px-4 py-2 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {quotes.map(q => (
              <tr key={q.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2">{q.clientName || "N/A"}</td>
                <td className="px-4 py-2">{q.items?.length || 0}</td>
                <td className="px-4 py-2 font-medium">${(q.totalAmount || 0).toFixed(2)}</td>
                <td className="px-4 py-2 capitalize">{q.status || "draft"}</td>
                <td className="px-4 py-2">
                  <button onClick={() => navigate(`/quotes/${q.id}`)} className="text-indigo-600 hover:underline mr-3">View</button>
                  {q.pdfUrl && (
                    <a href={q.pdfUrl} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline mr-3">PDF</a>
                  )}
                  <button onClick={() => remove(q.id)} className="text-red-600 hover:underline">Del</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function QuoteEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [client, setClient] = useState("");
  const [discount, setDiscount] = useState(0);
  const [items, setItems] = useState([]);
  const [saving, setSaving] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/products?page=1&pageSize=200`, { headers: authHeader });
      const data = await res.json();
      setProducts(data.items || []);

      if (id && id !== "new") {
        const r2 = await fetch(`${API}/quotes/${id}`, { headers: authHeader });
        if (r2.ok) {
          const q = await r2.json();
          setClient(q.clientName || "");
          setDiscount(q.discount || 0);
          setItems(q.items || []);
        }
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [id]);

  const subtotal = items.reduce((s, it) => s + (it.qty * it.price), 0);
  const afterDisc = subtotal * (1 - discount / 100);
  const total = afterDisc;

  const addItem = () => {
    setItems([...items, { productId: "", productName: "", qty: 1, price: 0 }]);
  };

  const updateItem = (idx, field, val) => {
    const newItems = [...items];
    newItems[idx][field] = val;
    if (field === "productId") {
      const p = products.find(x => x.id === val);
      if (p) { newItems[idx].productName = p.name; newItems[idx].price = p.price; }
    }
    setItems(newItems);
  };

  const removeItem = (idx) => {
    setItems(items.filter((_, i) => i !== idx));
  };

  const handleSave = async () => {
    setSaving(true);
    const body = { clientName: client, items, discount, taxRate: 0, note: "" };
    const url = id !== "new" ? `${API}/quotes/${id}` : `${API}/quotes`;
    const method = id !== "new" ? "PUT" : "POST";
    await fetch(url, { method, headers: { "Content-Type": "application/json", ...authHeader }, body: JSON.stringify(body) });
    setSaving(false);
    navigate("/quotes");
  };

  if (loading) return <p className="p-4">Loading...</p>;

  return (
    <div className="max-w-5xl mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">{id === "new" ? "New Quote" : "Edit Quote"}</h2>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white rounded shadow p-4">
            <h3 className="font-bold mb-3">Client Info</h3>
            <label className="block text-sm mb-1">Client Name</label>
            <input value={client} onChange={e => setClient(e.target.value)} className="border w-full px-3 py-2 rounded mb-3" />
            <label className="block text-sm mb-1">Discount (%)</label>
            <input type="number" value={discount} onChange={e => setDiscount(Number(e.target.value))} className="border w-full px-3 py-2 rounded mb-3" />