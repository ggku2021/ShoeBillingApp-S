export async function getJSON(key) {
  const val = await DB.get(key);
  return val ? JSON.parse(val) : null;
}

export async function putJSON(key, obj) {
  await DB.put(key, JSON.stringify(obj));
}

export async function getList(prefix, page = 1, pageSize = 20) {
  const listKey = `${prefix}:list`;
  const ids = JSON.parse(await DB.get(listKey) || "[]");
  const start = (page - 1) * pageSize;
  const slice = ids.slice(start, start + pageSize);
  const items = await Promise.all(slice.map((id) => getJSON(`${prefix}:${id}`)));
  return { items, total: ids.length };
}

export async function uploadToR2(filename, body, contentType) {
  await R2_BUCKET.put(filename, body, { httpMetadata: { contentType } });
  return `https://${R2_BUCKET.id}.r2.dev/${filename}`;
}