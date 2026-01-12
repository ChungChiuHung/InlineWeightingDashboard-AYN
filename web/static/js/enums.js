let _enumCache = null;

async function loadEnums() {
  if (_enumCache) return _enumCache;
  _enumCache = await fetchJSON("/enums");
  return _enumCache;
}
