/**
 * 简易商品管理 API
 * 支持: GET/POST/PUT/DELETE /api/products
 */
import { getJSON, putJSON, getList, uploadToR2 } from "./utils.js";
const USAGE = `
  GET    /api/products        -> list with pagination (page,size)
  GET    /api/products/:id    -> get by id
  POST   /api/products        -> create
  PUT    /api/products/:id    -> update
  DELETE /api/products/:id    -> delete
`;

export async function handle(req) {
  const url = new URL(req.url);
  const id = url.pathname.split("/").pop();
  const auth = req.headers.get("Authorization");
  if (!auth || !auth.startsWith("Bearer ")) {
    return new Response("Unauthorized", { status: 401 });
  }

  // 验证 id 格式（UUID）
  const isUUID = (s) => typeof s === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s);

  if (req.method === "GET") {
    if (id && isUUID(id)) {
      const product = await getJSON(`product:${id}`);
      return product ? new Response(JSON.stringify(product), { status: 200 }) : new Response("Not Found", { status: 404 });
    }
    const { page = 1, pageSize = 20 } = Object.fromEntries(url.searchParams);
    const data = await getList("product", Number(page), Number(pageSize));
    return new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } });
  }

  if (req.method === "POST") {
    const body = await req.json();
    if (!body.name || !body.price) return new Response("Missing required fields", { status: 400 });
    const newId = crypto.randomUUID();
    let imageUrl = "";
    if (body.imageBase64) {
      const raw = body.imageBase64.replace(/^data:image\/\w+;base64,/, "");
      imageUrl = await uploadToR2(`products/${newId}.png`, Buffer.from(raw, "base64"), "image/png");
    }
    const product = {
      id: newId,
      name: body.name,
      price: Number(body.price) || 0,
      description: body.description || "",
      size: body.size || "",
      category: body.category || "",
      unit: body.unit || "pair",
      image: imageUrl,
      createdAt: Date.now(),
      updatedAt: Date.now()
    };
    await putJSON(`product:${newId}`, product);
    const list = JSON.parse(await DB.get("product:list") || "[]");
    if (!list.includes(newId)) list.push(newId);
    await DB.put("product:list", JSON.stringify(list));
    return new Response(JSON.stringify(product), { status: 201, headers: { "Content-Type": "application/json" } });
  }

  if (req.method === "PUT" && id && isUUID(id)) {
    const exist = await getJSON(`product:${id}`);
    if (!exist) return new Response("Not Found", { status: 404 });
    const body = await req.json();
    let imageUrl = exist.image;
    if (body.imageBase64) {
      const raw = body.imageBase64.replace(/^data:image\/\w+;base64,/, "");
      imageUrl = await uploadToR2(`products/${id}.png`, Buffer.from(raw, "base64"), "image/png");
    }
    const updated = {
      ...exist,
      name: body.name ?? exist.name,
      price: body.price !== undefined ? Number(body.price) : exist.price,
      description: body.description ?? exist.description,
      size: body.size ?? exist.size,
      category: body.category ?? exist.category,
      unit: body.unit ?? exist.unit,
      image: imageUrl,
      updatedAt: Date.now()
    };
    await putJSON(`product:${id}`, updated);
    return new Response(JSON.stringify(updated), { status: 200, headers: { "Content-Type": "application/json" } });
  }

  if (req.method === "DELETE" && id && isUUID(id)) {
    await DB.delete(`product:${id}`);
    const list = JSON.parse(await DB.get("product:list") || "[]");
    await DB.put("product:list", JSON.stringify(list.filter((i) => i !== id)));
    return new Response(null, { status: 204 });
  }

  return new Response(USAGE, { status: 400, headers: { "Content-Type": "text/plain" } });
}

// export default { fetch: handle };