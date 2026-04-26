/**
 * 销售单 API
 * GET/POST/PUT/DELETE /api/orders
 */
import { getJSON, putJSON, getList, uploadToR2 } from "./utils.js";
import { PDFDocument } from "pdf-lib";

const USAGE = `
  GET    /api/orders        -> list
  GET    /api/orders/:id    -> get by id
  POST   /api/orders        -> create sale order
  PUT    /api/orders/:id    -> update
  DELETE /api/orders/:id    -> delete
`;

export async function handle(req) {
  const url = new URL(req.url);
  const id = url.pathname.split("/").pop();
  const auth = req.headers.get("Authorization");
  if (!auth || !auth.startsWith("Bearer ")) {
    return new Response("Unauthorized", { status: 401 });
  }

  if (req.method === "GET") {
    if (id && id !== "orders") {
      const order = await getJSON(`order:${id}`);
      return order ? new Response(JSON.stringify(order)) : new Response("Not Found", { status: 404 });
    }
    const { page = 1, pageSize = 20 } = Object.fromEntries(url.searchParams);
    const data = await getList("order", Number(page), Number(pageSize));
    return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
  }

  if (req.method === "POST") {
    const body = await req.json();
    if (!body.clientName || !body.items?.length) {
      return new Response("Missing clientName or items", { status: 400 });
    }
    const newId = crypto.randomUUID();
    const order = {
      id: newId,
      clientName: body.clientName,
      contact: body.contact || "",
      items: body.items,
      status: body.status || "draft",
      totalAmount: calculateTotal(body.items, body.discount, body.taxRate) || 0,
      note: body.note || "",
      createdAt: Date.now(),
      updatedAt: Date.now()
    };
    await putJSON(`order:${newId}`, order);
    const list = JSON.parse(await DB.get("order:list") || "[]");
    list.push(newId);
    await DB.put("order:list", JSON.stringify(list));

    const pdfUrl = await generateOrderPDF(order);
    order.pdfUrl = pdfUrl;
    await putJSON(`order:${newId}`, order);
    return new Response(JSON.stringify(order), { status: 201, headers: { "Content-Type": "application/json" } });
  }

  if (req.method === "PUT" && id) {
    const exist = await getJSON(`order:${id}`);
    if (!exist) return new Response("Not Found", { status: 404 });
    const body = await req.json();
    const updated = {
      ...exist,
      clientName: body.clientName ?? exist.clientName,
      contact: body.contact ?? exist.contact,
      items: body.items ?? exist.items,
      status: body.status ?? exist.status,
      totalAmount: body.items ? calculateTotal(body.items, body.discount, body.taxRate) : exist.totalAmount,
      note: body.note ?? exist.note,
      updatedAt: Date.now()
    };
    await putJSON(`order:${id}`, updated);
    return new Response(JSON.stringify(updated), { headers: { "Content-Type": "application/json" } });
  }

  if (req.method === "DELETE" && id) {
    await DB.delete(`order:${id}`);
    const list = JSON.parse(await DB.get("order:list") || "[]");
    await DB.put("order:list", JSON.stringify(list.filter((i) => i !== id)));
    return new Response(null, { status: 204 });
  }

  return new Response(USAGE, { status: 400, headers: { "Content-Type": "text/plain" } });
}

function calculateTotal(items) {
  return items.reduce((sum, i) => sum + i.qty * i.price, 0);
}

async function generateOrderPDF(order) {
  const pdfDoc = await PDFDocument.create();
  const page = pdfDoc.addPage([595.28, 841.89]);
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const bold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
  let y = 800;
  page.drawText("SALE ORDER", { x: 50, y, size: 22, font: bold });
  y -= 30;
  page.drawText(`Order ID: ${order.id.slice(0, 8)}`, { x: 50, y, size: 12, font });
  y -= 20;
  page.drawText(`Customer: ${order.clientName}`, { x: 50, y, size: 12, font });
  y -= 20;
  page.drawText(`Status: ${order.status}`, { x: 50, y, size: 12, font });
  y -= 30;
  page.drawText("Item Details", { x: 50, y, size: 12, font: bold });
  y -= 15;
  order.items.forEach((item) => {
    page.drawText(item.productName || "N/A", { x: 50, y, size: 10, font });
    page.drawText(String(item.qty), { x: 250, y, size: 10, font });
    page.drawText(`$${item.price.toFixed(2)}`, { x: 320, y, size: 10, font });
    y -= 15;
  });
  y -= 20;
  page.drawText(`Total: $${order.totalAmount.toFixed(2)}`, { x: 50, y, size: 12, font: bold });
  const filename = `orders/${order.id}.pdf`;
  const pdfBytes = await pdfDoc.save();
  await R2_BUCKET.put(filename, pdfBytes, { httpMetadata: { contentType: "application/pdf" } });
  return `https://${R2_BUCKET.id}.r2.dev/${filename}`;
}