/**
 * 报价单 API
 * GET/POST/PUT/DELETE /api/quotes
 */
import { getJSON, putJSON, getList, uploadToR2 } from "./utils.js";
import { PDFDocument, rgb, StandardFonts } from "pdf-lib";

const USAGE = `
  GET    /api/quotes        -> list (page,size)
  GET    /api/quotes/:id    -> get by id
  POST   /api/quotes        -> create quotation
  PUT    /api/quotes/:id    -> update
  DELETE /api/quotes/:id    -> delete
`;

export async function handle(req) {
  const url = new URL(req.url);
  const id = url.pathname.split("/").pop();
  const auth = req.headers.get("Authorization");
  if (!auth || !auth.startsWith("Bearer ")) {
    return new Response("Unauthorized", { status: 401 });
  }

  if (req.method === "GET") {
    if (id && id !== "quotes") {
      const quote = await getJSON(`quote:${id}`);
      return quote ? new Response(JSON.stringify(quote)) : new Response("Not Found", { status: 404 });
    }
    const { page = 1, pageSize = 20 } = Object.fromEntries(url.searchParams);
    const data = await getList("quote", Number(page), Number(pageSize));
    return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
  }

  if (req.method === "POST") {
    const body = await req.json();
    if (!body.clientName || !body.items?.length) {
      return new Response("Missing clientName or items", { status: 400 });
    }
    const newId = crypto.randomUUID();
    const quote = {
      id: newId,
      clientName: body.clientName,
      contact: body.contact || "",
      items: body.items,
      discount: Number(body.discount) || 0,
      taxRate: Number(body.taxRate) || 0,
      totalAmount: calculateTotal(body.items, body.discount, body.taxRate),
      validUntil: body.validUntil || Date.now() + 7 * 24 * 60 * 60 * 1000,
      status: "draft", // draft, sent, confirmed, expired
      note: body.note || "",
      createdAt: Date.now(),
      updatedAt: Date.now()
    };
    await putJSON(`quote:${newId}`, quote);
    const list = JSON.parse(await DB.get("quote:list") || "[]");
    list.push(newId);
    await DB.put("quote:list", JSON.stringify(list));

    // 生成 PDF
    const pdfUrl = await generateQuotePDF(quote);
    quote.pdfUrl = pdfUrl;
    await putJSON(`quote:${newId}`, quote);

    return new Response(JSON.stringify(quote), { status: 201, headers: { "Content-Type": "application/json" } });
  }

  if (req.method === "PUT" && id) {
    const exist = await getJSON(`quote:${id}`);
    if (!exist) return new Response("Not Found", { status: 404 });
    const body = await req.json();
    const updated = {
      ...exist,
      clientName: body.clientName ?? exist.clientName,
      contact: body.contact ?? exist.contact,
      items: body.items ?? exist.items,
      discount: body.discount !== undefined ? Number(body.discount) : exist.discount,
      taxRate: body.taxRate !== undefined ? Number(body.taxRate) : exist.taxRate,
      totalAmount: body.items ? calculateTotal(body.items, body.discount, body.taxRate) : exist.totalAmount,
      validUntil: body.validUntil ?? exist.validUntil,
      status: body.status ?? exist.status,
      note: body.note ?? exist.note,
      updatedAt: Date.now()
    };
    await putJSON(`quote:${id}`, updated);
    return new Response(JSON.stringify(updated), { headers: { "Content-Type": "application/json" } });
  }

  if (req.method === "DELETE" && id) {
    await DB.delete(`quote:${id}`);
    const list = JSON.parse(await DB.get("quote:list") || "[]");
    await DB.put("quote:list", JSON.stringify(list.filter((i) => i !== id)));
    return new Response(null, { status: 204 });
  }

  return new Response(USAGE, { status: 400, headers: { "Content-Type": "text/plain" } });
}

function calculateTotal(items, discount = 0, taxRate = 0) {
  const subtotal = items.reduce((sum, item) => sum + item.qty * item.price, 0);
  const afterDiscount = subtotal * (1 - discount / 100);
  return afterDiscount * (1 + taxRate / 100);
}

async function generateQuotePDF(quote) {
  const pdfDoc = await PDFDocument.create();
  const page = pdfDoc.addPage([595.28, 841.89]); // A4
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const boldFont = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

  let y = 800;
  page.drawText("QUOTATION", { x: 50, y, size: 24, font: boldFont });
  y -= 40;

  page.drawText(`Quote ID: ${quote.id.slice(0, 8)}`, { x: 50, y, size: 12, font });
  y -= 20;
  page.drawText(`Client: ${quote.clientName}`, { x: 50, y, size: 12, font });
  y -= 20;
  page.drawText(`Date: ${new Date(quote.createdAt).toLocaleDateString()}`, { x: 50, y, size: 12, font });
  y -= 30;

  // 表头
  page.drawText("Product", { x: 50, y, size: 10, font: boldFont });
  page.drawText("Qty", { x: 250, y, size: 10, font: boldFont });
  page.drawText("Price", { x: 320, y, size: 10, font: boldFont });
  page.drawText("Total", { x: 390, y, size: 10, font: boldFont });
  y -= 15;

  quote.items.forEach((item) => {
    page.drawText(item.productName || "N/A", { x: 50, y, size: 10, font });
    page.drawText(String(item.qty), { x: 250, y, size: 10, font });
    page.drawText(`$${item.price.toFixed(2)}`, { x: 320, y, size: 10, font });
    page.drawText(`$${(item.qty * item.price).toFixed(2)}`, { x: 390, y, size: 10, font });
    y -= 15;
  });

  y -= 20;
  page.drawText(`Total: $${quote.totalAmount.toFixed(2)}`, { x: 50, y, size: 12, font: boldFont });

  const pdfBytes = await pdfDoc.save();
  const filename = `quotes/${quote.id}.pdf`;
  await R2_BUCKET.put(filename, pdfBytes, { httpMetadata: { contentType: "application/pdf" } });
  return `https://${R2_BUCKET.id}.r2.dev/${filename}`;
}