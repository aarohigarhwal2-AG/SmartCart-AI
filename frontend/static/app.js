// SmartCart AI Frontend Application Logic

const DEFAULT_IMG = "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=500&auto=format&fit=crop&q=80";

const STATE = {
  sessionId: "session_" + Math.random().toString(36).substring(2, 9),
  cartId: localStorage.getItem("smartcart_active_cart_id") || null,
  persona: "customer",
  activeTab: "chat",
  detectedBudget: 3000,
  products: [],
  cart: null,
  catalogView: "grid",
  selectedCategory: "all",
  currentQvProduct: null
};

// Store curated bundles for one-click add
window._smartcart_bundles = {};

function handleImgError(img) {
  img.onerror = null;
  img.src = DEFAULT_IMG;
}

// Toast notification helper
function showToast(msg, duration = 3000) {
  const toast = document.getElementById("appToast");
  if (!toast) return;
  toast.textContent = msg;
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, duration);
}

// ==========================================
// PERSONA & TAB SWITCHING
// ==========================================

function switchPersona(persona) {
  STATE.persona = persona;
  const btnCust = document.getElementById("btnPersonaCustomer");
  const btnMerch = document.getElementById("btnPersonaMerchant");

  if (persona === "customer") {
    if (btnCust) btnCust.classList.add("active");
    if (btnMerch) btnMerch.classList.remove("active");
    document.querySelectorAll(".nav-customer").forEach(el => el.style.display = "inline-flex");
    document.querySelectorAll(".nav-merchant").forEach(el => el.style.display = "none");
    switchTab("chat");
  } else {
    if (btnMerch) btnMerch.classList.add("active");
    if (btnCust) btnCust.classList.remove("active");
    document.querySelectorAll(".nav-customer").forEach(el => el.style.display = "none");
    document.querySelectorAll(".nav-merchant").forEach(el => el.style.display = "inline-flex");
    switchTab("analytics");
  }
}

function switchTab(tabName) {
  STATE.activeTab = tabName;
  document.querySelectorAll(".nav-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

  const targetPane = document.getElementById(`pane-${tabName}`);
  if (targetPane) targetPane.classList.add("active");

  // Highlight appropriate tab button
  if (STATE.persona === "customer") {
    const custBtn = document.getElementById(`tab-nav-${tabName}`);
    if (custBtn) custBtn.classList.add("active");
  } else {
    if (tabName === "analytics") {
      const aBtn = document.getElementById("tab-nav-analytics");
      if (aBtn) aBtn.classList.add("active");
    } else if (tabName === "catalog") {
      const iBtn = document.getElementById("tab-nav-inventory");
      if (iBtn) iBtn.classList.add("active");
    }
  }

  // Floating AI Trigger: Visible ONLY on Customer Storefront -> Browse Products (catalog) tab
  const floatingWidget = document.getElementById("floatingAiWidget");
  if (floatingWidget) {
    if (STATE.persona === "customer" && tabName === "catalog") {
      floatingWidget.style.display = "flex";
    } else {
      floatingWidget.style.display = "none";
    }
  }

  // Refresh tab data
  if (tabName === "catalog") fetchCatalog();
  if (tabName === "chat") updateBudgetTracker();
  if (tabName === "cart") loadCartView();
  if (tabName === "analytics") {
    loadAnalytics();
    loadAuditLogs();
  }
}

// Download Sample CSV helper
function downloadSampleCSV(event) {
  if (event) event.stopPropagation();
  window.location.href = "/api/catalog/download-sample";
}

// ==========================================
// 1. MERCHANT CATALOG FUNCTIONS
// ==========================================

async function fetchCatalog() {
  try {
    const res = await fetch("/api/catalog/products");
    if (!res.ok) throw new Error("Failed to load products");
    STATE.products = await res.json();
    renderCatalogTable(STATE.products);
    updateCatalogStats(STATE.products);
  } catch (err) {
    console.error("Error fetching catalog:", err);
  }
}

function updateCatalogStats(products) {
  const total = products.length;
  const inStock = products.filter(p => p.stock > 0).length;
  const outOfStock = total - inStock;
  const categories = new Set(products.map(p => p.category)).size;

  const totalBadge = document.getElementById("productTotalBadge");
  if (totalBadge) totalBadge.textContent = `${total} Products`;
  const statIn = document.getElementById("statInStock");
  if (statIn) statIn.textContent = inStock;
  const statOut = document.getElementById("statOutOfStock");
  if (statOut) statOut.textContent = outOfStock;
  const statCats = document.getElementById("statCategories");
  if (statCats) statCats.textContent = categories;
}

function setCatalogView(view) {
  STATE.catalogView = view;
  const btnGrid = document.getElementById("btnViewGrid");
  const btnTable = document.getElementById("btnViewTable");
  const gridView = document.getElementById("catalogGridView");
  const tableView = document.getElementById("catalogTableView");

  if (view === "grid") {
    if (btnGrid) btnGrid.classList.add("active");
    if (btnTable) btnTable.classList.remove("active");
    if (gridView) gridView.style.display = "grid";
    if (tableView) tableView.style.display = "none";
  } else {
    if (btnTable) btnTable.classList.add("active");
    if (btnGrid) btnGrid.classList.remove("active");
    if (gridView) gridView.style.display = "none";
    if (tableView) tableView.style.display = "block";
  }
}

function filterByCategory(category) {
  STATE.selectedCategory = category;
  document.querySelectorAll(".category-chip").forEach(chip => {
    if (chip.textContent.toLowerCase().includes(category.toLowerCase()) || 
       (category === "all" && chip.textContent.includes("All"))) {
      chip.classList.add("active");
    } else {
      chip.classList.remove("active");
    }
  });
  filterCatalogTable();
}

function renderCatalogTable(products) {
  renderCatalogGrid(products);
  renderCatalogTableView(products);
}

function renderCatalogGrid(products) {
  const container = document.getElementById("catalogGridView");
  if (!container) return;
  if (!products || products.length === 0) {
    container.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:3rem 1rem; color:var(--text-muted);">
      <p style="font-size:2rem; margin-bottom:0.5rem;">🔍</p>
      <p style="font-weight:600;">No products match your filter criteria.</p>
    </div>`;
    return;
  }

  container.innerHTML = products.map(p => {
    const imgUrl = p.image_url || DEFAULT_IMG;
    const inStock = p.stock > 0;
    const cardClass = inStock ? "prod-grid-card" : "prod-grid-card is-out-of-stock";
    return `
      <div class="${cardClass}">
        <div class="prod-img-box" onclick="openQuickView('${p.id}')">
          <img src="${imgUrl}" alt="${escapeHtml(p.name)}" loading="lazy" onerror="handleImgError(this)">
          <span class="prod-stock-badge ${inStock ? 'badge-in-stock' : 'badge-out-stock'}">
            ${inStock ? `In Stock (${p.stock})` : 'Out of Stock'}
          </span>
          <span class="prod-quickview-tag">👁️ Quick View</span>
        </div>
        <div class="prod-card-body">
          <span class="prod-card-category">${escapeHtml(p.category)}</span>
          <h4 class="prod-card-title" title="${escapeHtml(p.name)}">${escapeHtml(p.name)}</h4>
          <p class="prod-card-desc">${escapeHtml(p.description)}</p>
          <div class="prod-card-footer">
            <span class="prod-card-price">₹${p.price.toLocaleString("en-IN")}</span>
            <button class="btn btn-primary btn-sm" ${!inStock ? 'disabled style="opacity:0.6;"' : ''} onclick="addItemToCart('${p.id}', '${escapeHtml(p.name)}')">
              ${inStock ? '+ Add' : 'Sold Out'}
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function renderCatalogTableView(products) {
  const tbody = document.getElementById("catalogTableBody");
  if (!tbody) return;
  if (!products || products.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:2rem;">No products found.</td></tr>`;
    return;
  }

  tbody.innerHTML = products.map(p => {
    const imgUrl = p.image_url || DEFAULT_IMG;
    const inStock = p.stock > 0;
    return `
      <tr class="${!inStock ? 'row-out-of-stock' : ''}">
        <td>
          <img src="${imgUrl}" alt="${escapeHtml(p.name)}" class="table-prod-thumb" onerror="handleImgError(this)" onclick="openQuickView('${p.id}')">
        </td>
        <td><span style="font-family:monospace; font-weight:600; color:var(--primary);">${p.id}</span></td>
        <td style="font-weight:600; cursor:pointer;" onclick="openQuickView('${p.id}')">${escapeHtml(p.name)}</td>
        <td><span class="badge badge-primary">${escapeHtml(p.category)}</span></td>
        <td style="font-size:0.8rem; color:var(--text-muted); max-width:260px;">${escapeHtml(p.description)}</td>
        <td style="font-weight:700; color:var(--text-main);">₹${p.price.toLocaleString("en-IN")}</td>
        <td>
          ${inStock 
            ? `<span class="badge badge-success">In Stock (${p.stock})</span>` 
            : `<span class="badge badge-danger">Out of Stock</span>`}
        </td>
        <td>
          <button class="btn btn-primary btn-sm" ${!inStock ? 'disabled style="opacity:0.6;"' : ''} onclick="addItemToCart('${p.id}', '${escapeHtml(p.name)}')">
            ${inStock ? '+ Add' : 'Sold Out'}
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function filterCatalogTable() {
  const query = (document.getElementById("catalogSearchInput")?.value || "").toLowerCase();
  const inStockOnly = document.getElementById("filterInStockOnly")?.checked;
  const categoryFilter = STATE.selectedCategory;

  const filtered = STATE.products.filter(p => {
    const matchesQuery = p.name.toLowerCase().includes(query) ||
                         p.description.toLowerCase().includes(query) ||
                         p.category.toLowerCase().includes(query) ||
                         p.tags.toLowerCase().includes(query);
    const matchesStock = inStockOnly ? p.stock > 0 : true;
    const matchesCategory = categoryFilter === "all" || p.category.toLowerCase() === categoryFilter.toLowerCase();
    return matchesQuery && matchesStock && matchesCategory;
  });

  renderCatalogTable(filtered);
}

function openQuickView(productId) {
  const p = STATE.products.find(item => item.id === productId);
  if (!p) return;
  STATE.currentQvProduct = p;

  document.getElementById("qvImage").src = p.image_url || DEFAULT_IMG;
  document.getElementById("qvCategory").textContent = p.category;
  document.getElementById("qvTitle").textContent = p.name;
  document.getElementById("qvPrice").textContent = `₹${p.price.toLocaleString("en-IN")}`;
  document.getElementById("qvDescription").textContent = p.description;
  document.getElementById("qvTags").textContent = p.tags;

  const badge = document.getElementById("qvStockBadge");
  const addBtn = document.getElementById("qvAddToCartBtn");
  if (p.stock > 0) {
    badge.className = "badge badge-success";
    badge.textContent = `In Stock (${p.stock})`;
    addBtn.disabled = false;
    addBtn.style.opacity = "1";
    addBtn.textContent = "🛒 Add to Cart";
  } else {
    badge.className = "badge badge-danger";
    badge.textContent = "Out of Stock";
    addBtn.disabled = true;
    addBtn.style.opacity = "0.6";
    addBtn.textContent = "Sold Out";
  }

  document.getElementById("productQuickViewModal").classList.add("active");
}

function closeQuickView(event) {
  if (event && event.target && event.target.id !== "productQuickViewModal" && !event.target.classList.contains("modal-close-btn")) {
    return;
  }
  document.getElementById("productQuickViewModal").classList.remove("active");
  STATE.currentQvProduct = null;
}

function addCurrentQvToCart() {
  if (STATE.currentQvProduct) {
    addItemToCart(STATE.currentQvProduct.id, STATE.currentQvProduct.name);
    closeQuickView();
  }
}

async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  await uploadCSVFile(file);
}

function handleFileDrop(event) {
  event.preventDefault();
  const file = event.dataTransfer.files[0];
  if (file) uploadCSVFile(file);
}

async function uploadCSVFile(file) {
  const alertBox = document.getElementById("uploadAlert");
  alertBox.style.display = "block";
  alertBox.style.background = "#e0e7ff";
  alertBox.style.color = "#3730a3";
  alertBox.textContent = `Uploading and parsing '${file.name}'...`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/catalog/upload", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (!res.ok) {
      alertBox.style.background = "#fee2e2";
      alertBox.style.color = "#991b1b";
      alertBox.textContent = `Upload Error: ${data.detail || "Invalid CSV"}`;
      return;
    }

    let msg = `✅ Successfully imported ${data.valid_count} products.`;
    if (data.rejected_count > 0) {
      msg += ` (${data.rejected_count} rows rejected due to validation errors)`;
    }
    alertBox.style.background = "#dcfce7";
    alertBox.style.color = "#166534";
    alertBox.textContent = msg;

    STATE.products = data.products;
    renderCatalogTable(STATE.products);
    updateCatalogStats(STATE.products);
    showToast("Catalog updated successfully!");
  } catch (err) {
    alertBox.style.background = "#fee2e2";
    alertBox.style.color = "#991b1b";
    alertBox.textContent = `Error: ${err.message}`;
  }
}

async function loadSampleCatalog() {
  const alertBox = document.getElementById("uploadAlert");
  alertBox.style.display = "block";
  alertBox.style.background = "#e0e7ff";
  alertBox.style.color = "#3730a3";
  alertBox.textContent = "Loading 15-product sample catalog...";

  try {
    const res = await fetch("/api/catalog/load-sample", { method: "POST" });
    const data = await res.json();
    
    alertBox.style.background = "#dcfce7";
    alertBox.style.color = "#166534";
    alertBox.textContent = `✅ Loaded ${data.valid_count} sample products into catalog!`;

    STATE.products = data.products;
    renderCatalogTable(STATE.products);
    updateCatalogStats(STATE.products);
    showToast("Sample catalog loaded!");
  } catch (err) {
    alertBox.style.background = "#fee2e2";
    alertBox.style.color = "#991b1b";
    alertBox.textContent = "Failed to load sample catalog.";
  }
}

async function loadRealCatalog() {
  const alertBox = document.getElementById("uploadAlert");
  alertBox.style.display = "block";
  alertBox.style.background = "#e0e7ff";
  alertBox.style.color = "#3730a3";
  alertBox.textContent = "Loading real-world WFH setup catalog...";

  try {
    const res = await fetch("/api/catalog/load-real", { method: "POST" });
    const data = await res.json();

    alertBox.style.background = "#dcfce7";
    alertBox.style.color = "#166534";
    alertBox.textContent = `✅ Loaded ${data.valid_count} real-world products!`;

    STATE.products = data.products;
    renderCatalogTable(STATE.products);
    updateCatalogStats(STATE.products);
    showToast("WFH setup catalog loaded!");
  } catch (err) {
    alertBox.style.background = "#fee2e2";
    alertBox.style.color = "#991b1b";
    alertBox.textContent = "Failed to load catalog.";
  }
}

// ==========================================
// 2. CUSTOMER AI CHAT FUNCTIONS
// ==========================================

function sendQuickPrompt(promptText) {
  document.getElementById("chatInput").value = promptText;
  handleChatSubmit(new Event("submit"));
}

function clearChat() {
  const chatArea = document.getElementById("chatMessages");
  chatArea.innerHTML = `
    <div class="chat-bubble assistant">
      👋 Hi there! I'm your SmartCart shopping assistant. What can I help you build today?
      <br><small style="color:var(--text-muted); display:inline-block; margin-top:0.4rem;">Ask for individual items or full setups with your budget constraint (e.g. <em>"WFH setup under ₹3,000"</em>).</small>
    </div>
  `;
}

async function handleChatSubmit(event) {
  event.preventDefault();
  const input = document.getElementById("chatInput");
  const msg = input.value.trim();
  if (!msg) return;

  // Append user bubble
  appendChatBubble("user", msg);
  input.value = "";

  const sendBtn = document.getElementById("btnSendChat");
  sendBtn.disabled = true;
  sendBtn.textContent = "...";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: STATE.sessionId,
        message: msg,
        cart_id: STATE.cartId
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Chat error");

    // Append AI response bubble with recommendation cards
    appendAssistantResponse(data);
  } catch (err) {
    appendChatBubble("assistant", `⚠️ Sorry, I encountered an issue: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Send";
  }
}

function appendChatBubble(role, text) {
  const chatArea = document.getElementById("chatMessages");
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.innerHTML = escapeHtml(text).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  chatArea.appendChild(bubble);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function appendAssistantResponse(data) {
  const chatArea = document.getElementById("chatMessages");
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble assistant";

  let intentInfo = "";
  if (data.intent && data.intent.intent) {
    if (data.intent.budget) {
      STATE.detectedBudget = data.intent.budget;
      updateBudgetTracker();
    }
    const budgetStr = data.intent.budget ? ` • Budget: ₹${data.intent.budget.toLocaleString("en-IN")}` : "";
    intentInfo = `<div class="intent-tag-pill">🎯 Intent: ${data.intent.intent}${budgetStr}</div>`;
  }

  let html = `<div>${escapeHtml(data.reply).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</div>${intentInfo}`;

  // Multi-item bundle one-click add button
  if (data.recommendations && data.recommendations.length > 1) {
    const bundleId = "bundle_" + Date.now();
    window._smartcart_bundles[bundleId] = data.recommendations.map(r => ({
      id: r.product.id,
      name: r.product.name
    }));
    const bundleTotal = data.recommendations.reduce((sum, r) => sum + (r.product ? r.product.price : 0), 0);
    html += `
      <div class="bundle-banner-card">
        <div>
          <h4 style="font-size:0.9rem; font-weight:700; color:#065f46; margin-bottom:0.2rem;">
            ✨ Recommended Curated Bundle (${data.recommendations.length} Items)
          </h4>
          <p style="font-size:0.75rem; color:#047857; margin:0;">
            One-click add all matching recommendations within your ₹${(STATE.detectedBudget || bundleTotal).toLocaleString("en-IN")} budget
          </p>
        </div>
        <button class="btn btn-primary btn-sm" style="white-space:nowrap; background:#059669; border-color:#059669;" onclick="addEntireBundle('${bundleId}')">
          🛍️ + Add Entire Bundle (₹${bundleTotal.toLocaleString("en-IN")})
        </button>
      </div>
    `;
  }

  // Primary Recommendations
  if (data.recommendations && data.recommendations.length > 0) {
    html += `<div class="rec-cards-list">`;
    data.recommendations.forEach(rec => {
      const p = rec.product;
      const cardClass = rec.is_upsell ? "rec-card upsell" : "rec-card";
      const tagText = rec.is_upsell ? "⭐ UPSELL UPGRADE" : "✅ RECOMMENDED";
      const imgUrl = p.image_url || DEFAULT_IMG;
      
      html += `
        <div class="${cardClass}">
          <img src="${imgUrl}" alt="${escapeHtml(p.name)}" class="rec-thumb" onerror="handleImgError(this)" onclick="openQuickView('${p.id}')">
          <div class="rec-info" style="flex:1;">
            <div style="font-size:0.65rem; font-weight:700; color:var(--primary);">${tagText}</div>
            <h4 style="cursor:pointer;" onclick="openQuickView('${p.id}')">${escapeHtml(p.name)}</h4>
            <p>${escapeHtml(rec.reason)}</p>
          </div>
          <div style="text-align:right;">
            <div class="rec-price">₹${p.price.toLocaleString("en-IN")}</div>
            <button class="btn btn-primary btn-sm" style="margin-top:0.35rem;" onclick="addItemToCart('${p.id}', '${escapeHtml(p.name)}')">
              + Add
            </button>
          </div>
        </div>
      `;
    });
    html += `</div>`;
  }

  // Cross-sell Recommendations
  if (data.cross_sells && data.cross_sells.length > 0) {
    html += `<div style="font-size:0.75rem; font-weight:700; color:var(--text-muted); margin-top:0.75rem;">COMPLEMENTARY CROSS-SELL ADD-ONS</div>`;
    html += `<div class="rec-cards-list">`;
    data.cross_sells.forEach(cs => {
      const p = cs.product;
      const imgUrl = p.image_url || DEFAULT_IMG;
      html += `
        <div class="rec-card cross-sell">
          <img src="${imgUrl}" alt="${escapeHtml(p.name)}" class="rec-thumb" onerror="handleImgError(this)" onclick="openQuickView('${p.id}')">
          <div class="rec-info" style="flex:1;">
            <div style="font-size:0.65rem; font-weight:700; color:var(--secondary);">💡 COMPLEMENTARY ADD-ON</div>
            <h4 style="cursor:pointer;" onclick="openQuickView('${p.id}')">${escapeHtml(p.name)}</h4>
            <p>${escapeHtml(cs.reason)} <em style="color:var(--text-main); font-weight:500;">${escapeHtml(cs.savings_tip || "")}</em></p>
          </div>
          <div style="text-align:right;">
            <div class="rec-price">₹${p.price.toLocaleString("en-IN")}</div>
            <button class="btn btn-secondary btn-sm" style="margin-top:0.35rem;" onclick="addItemToCart('${p.id}', '${escapeHtml(p.name)}')">
              + Add Companion
            </button>
          </div>
        </div>
      `;
    });
    html += `</div>`;
  }

  bubble.innerHTML = html;
  chatArea.appendChild(bubble);
  chatArea.scrollTop = chatArea.scrollHeight;
}

// ==========================================
// 3. CART & LIVE BUDGET TRACKER
// ==========================================

async function addEntireBundle(bundleId) {
  const items = window._smartcart_bundles[bundleId];
  if (!items || items.length === 0) return;

  for (const item of items) {
    await addItemToCart(item.id, item.name, true);
  }
  showToast(`🎉 Added all ${items.length} bundle items to your cart!`);
}

async function addItemToCart(productId, productName, silent = false) {
  try {
    // Ensure cart exists
    if (!STATE.cartId) {
      const initRes = await fetch(`/api/cart?session_id=${STATE.sessionId}`, { method: "POST" });
      const initCart = await initRes.json();
      STATE.cartId = initCart.cart_id;
      localStorage.setItem("smartcart_active_cart_id", STATE.cartId);
    }

    const res = await fetch(`/api/cart/${STATE.cartId}/items?session_id=${STATE.sessionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: productId, quantity: 1 })
    });

    const data = await res.json();
    if (!res.ok) {
      if (!silent) showToast(`⚠️ ${data.detail || "Could not add item."}`);
      return;
    }

    STATE.cart = data;
    updateCartUI(data);
    if (!silent) showToast(`Added '${productName}' to cart!`);
  } catch (err) {
    if (!silent) showToast(`⚠️ Error: ${err.message}`);
  }
}

async function updateItemQty(productId, newQty) {
  if (!STATE.cartId) return;
  try {
    const res = await fetch(`/api/cart/${STATE.cartId}/items/${productId}?quantity=${newQty}&session_id=${STATE.sessionId}`, {
      method: "PUT"
    });
    const data = await res.json();
    if (res.ok) {
      STATE.cart = data;
      updateCartUI(data);
      loadCartView();
    }
  } catch (err) {
    console.error(err);
  }
}

async function removeItemFromCart(productId) {
  if (!STATE.cartId) return;
  try {
    const res = await fetch(`/api/cart/${STATE.cartId}/items/${productId}?session_id=${STATE.sessionId}`, {
      method: "DELETE"
    });
    const data = await res.json();
    if (res.ok) {
      STATE.cart = data;
      updateCartUI(data);
      loadCartView();
      showToast("Item removed from cart");
    }
  } catch (err) {
    console.error(err);
  }
}

async function loadCartView() {
  if (!STATE.cartId) {
    renderEmptyCartView();
    return;
  }

  try {
    const res = await fetch(`/api/cart/${STATE.cartId}`);
    if (!res.ok) {
      renderEmptyCartView();
      return;
    }
    const cart = await res.json();
    STATE.cart = cart;
    updateCartUI(cart);
    renderFullCartView(cart);
  } catch (err) {
    renderEmptyCartView();
  }
}

function updateBudgetTracker() {
  const detectedBudgetEl = document.getElementById("trackerDetectedBudget");
  const cartTotalEl = document.getElementById("trackerCartTotal");
  const remainingEl = document.getElementById("trackerRemainingBudget");
  const barFillEl = document.getElementById("trackerProgressBar");
  const pillEl = document.getElementById("budgetStatusPill");

  if (!detectedBudgetEl || !cartTotalEl || !remainingEl || !barFillEl) return;

  const budget = STATE.detectedBudget || 3000;
  const cartTotal = STATE.cart ? STATE.cart.total : 0;
  const remaining = budget - cartTotal;
  const pct = Math.min(100, Math.round((cartTotal / budget) * 100));

  detectedBudgetEl.textContent = `₹${budget.toLocaleString("en-IN")}`;
  cartTotalEl.textContent = `₹${cartTotal.toLocaleString("en-IN")}`;

  if (remaining >= 0) {
    remainingEl.textContent = `₹${remaining.toLocaleString("en-IN")}`;
    remainingEl.style.color = "var(--success)";
    barFillEl.style.width = `${pct}%`;
    barFillEl.style.background = "var(--success)";
    if (pillEl) {
      pillEl.className = "badge badge-success";
      pillEl.textContent = "Within Budget ✓";
    }
  } else {
    remainingEl.textContent = `-₹${Math.abs(remaining).toLocaleString("en-IN")}`;
    remainingEl.style.color = "var(--danger)";
    barFillEl.style.width = "100%";
    barFillEl.style.background = "var(--danger)";
    if (pillEl) {
      pillEl.className = "badge badge-danger";
      pillEl.textContent = "Over Budget ⚠️";
    }
  }
}

function updateCartUI(cart) {
  const count = cart ? cart.item_count : 0;
  const badgeEl = document.getElementById("cartBadgeCount");
  if (badgeEl) badgeEl.textContent = count;
  const totalItemsEl = document.getElementById("cartTotalItems");
  if (totalItemsEl) totalItemsEl.textContent = count;

  // Sync Live Budget Tracker
  updateBudgetTracker();

  // Render Mini Cart in chat sidebar
  const mini = document.getElementById("miniCartContent");
  if (!mini) return;

  if (!cart || cart.items.length === 0) {
    mini.innerHTML = `<p style="font-size:0.85rem; color:var(--text-muted); text-align:center; padding:1.5rem 0;">Your cart is empty.</p>`;
    return;
  }

  mini.innerHTML = `
    <div style="display:flex; flex-direction:column; gap:0.5rem;">
      ${cart.items.map(item => `
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.85rem; gap:0.5rem;">
          <div style="display:flex; align-items:center; gap:0.4rem; overflow:hidden;">
            <img src="${item.image_url || DEFAULT_IMG}" alt="" style="width:28px; height:28px; border-radius:4px; object-fit:cover;" onerror="handleImgError(this)">
            <span style="white-space:nowrap; text-overflow:ellipsis; overflow:hidden;">${item.quantity}x ${escapeHtml(item.name)}</span>
          </div>
          <span style="font-weight:600; white-space:nowrap;">₹${item.line_total.toLocaleString("en-IN")}</span>
        </div>
      `).join("")}
      <div style="border-top:1px solid var(--border); margin-top:0.5rem; padding-top:0.5rem; display:flex; justify-content:space-between; font-weight:700;">
        <span>Total:</span>
        <span style="color:var(--primary);">₹${cart.total.toLocaleString("en-IN")}</span>
      </div>
    </div>
  `;
}

function renderEmptyCartView() {
  const itemsContainer = document.getElementById("cartItemsList");
  if (itemsContainer) {
    itemsContainer.innerHTML = `
      <div style="text-align:center; padding:3rem 1rem; color:var(--text-muted);">
        <p style="font-size:2rem; margin-bottom:0.5rem;">🛒</p>
        <p style="font-weight:600; font-size:1rem;">Your cart is empty</p>
        <p style="font-size:0.8rem; margin-top:0.25rem;">Chat with the assistant or browse catalog to add products.</p>
        <button class="btn btn-primary btn-sm" style="margin-top:1rem;" onclick="switchTab('chat')">Start Shopping →</button>
      </div>
    `;
  }
  const subTotalEl = document.getElementById("summarySubtotal");
  if (subTotalEl) subTotalEl.textContent = "₹0.00";
  const totalEl = document.getElementById("summaryTotal");
  if (totalEl) totalEl.textContent = "₹0.00";
  const chkBtn = document.getElementById("btnProceedCheckout");
  if (chkBtn) chkBtn.disabled = true;
}

function renderFullCartView(cart) {
  if (!cart.items || cart.items.length === 0) {
    renderEmptyCartView();
    return;
  }

  const itemsHtml = cart.items.map(item => `
    <div style="display:flex; justify-content:space-between; align-items:center; padding:1rem 0; border-bottom:1px solid var(--border); gap:0.75rem;">
      <div style="display:flex; align-items:center; gap:0.75rem;">
        <img src="${item.image_url || DEFAULT_IMG}" alt="${escapeHtml(item.name)}" class="cart-item-thumb" onerror="handleImgError(this)" onclick="openQuickView('${item.product_id}')">
        <div>
          <h4 style="font-size:0.95rem; font-weight:600; cursor:pointer;" onclick="openQuickView('${item.product_id}')">${escapeHtml(item.name)}</h4>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.15rem;">Unit Price: ₹${item.unit_price.toLocaleString("en-IN")} • Category: ${escapeHtml(item.category)}</div>
        </div>
      </div>
      <div style="display:flex; align-items:center; gap:0.75rem;">
        <div style="display:flex; align-items:center; gap:0.3rem;">
          <button class="btn btn-secondary btn-sm" onclick="updateItemQty('${item.product_id}', ${item.quantity - 1})">-</button>
          <span style="font-weight:600; min-width:20px; text-align:center;">${item.quantity}</span>
          <button class="btn btn-secondary btn-sm" onclick="updateItemQty('${item.product_id}', ${item.quantity + 1})">+</button>
        </div>
        <div style="font-weight:700; min-width:80px; text-align:right;">₹${item.line_total.toLocaleString("en-IN")}</div>
        <button style="background:none; border:none; color:var(--danger); cursor:pointer; font-size:1.1rem; margin-left:0.25rem;" title="Remove" onclick="removeItemFromCart('${item.product_id}')">×</button>
      </div>
    </div>
  `).join("");

  document.getElementById("cartItemsList").innerHTML = itemsHtml;
  document.getElementById("summarySubtotal").textContent = `₹${cart.subtotal.toLocaleString("en-IN")}`;
  document.getElementById("summaryTotal").textContent = `₹${cart.total.toLocaleString("en-IN")}`;
  toggleCheckoutButton();
}

function toggleCheckoutButton() {
  const confirmed = document.getElementById("chkUserConfirm")?.checked;
  const hasItems = STATE.cart && STATE.cart.items && STATE.cart.items.length > 0;
  const btn = document.getElementById("btnProceedCheckout");
  if (btn) btn.disabled = !(confirmed && hasItems);
}

// ==========================================
// 4. RAZORPAY TEST MODE CHECKOUT
// ==========================================

async function initiateCheckout() {
  if (!STATE.cart || !STATE.cart.cart_id) {
    showToast("Cart is empty or not initialized.");
    return;
  }

  const confirmed = document.getElementById("chkUserConfirm").checked;
  if (!confirmed) {
    showToast("⚠️ Please check the confirmation box before checkout.");
    return;
  }

  const simMode = document.getElementById("paymentSimulationMode").value;
  const btn = document.getElementById("btnProceedCheckout");
  btn.disabled = true;
  btn.textContent = "Creating Razorpay Order...";

  try {
    // 1. Server-side Order Creation
    const res = await fetch(`/api/checkout/create-order?session_id=${STATE.sessionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cart_id: STATE.cart.cart_id,
        user_confirmed: true
      })
    });

    const orderData = await res.json();
    if (!res.ok) throw new Error(orderData.detail || "Failed to create order");

    // 2. Process Simulated or Razorpay Checkout
    if (simMode === "cancel") {
      btn.disabled = false;
      btn.textContent = "🔒 Pay with Razorpay Test Mode";
      showToast("⚠️ Payment was cancelled by user.");
      return;
    }

    if (simMode === "failure") {
      btn.disabled = false;
      btn.textContent = "🔒 Pay with Razorpay Test Mode";
      showToast("❌ Payment failed: Bank simulator declined transaction.");
      return;
    }

    // Success simulation / Real Razorpay test modal
    btn.textContent = "Verifying Payment Signature...";
    const mockPaymentId = `pay_test_${Math.random().toString(36).substring(2, 12)}`;
    const mockSignature = "mock_signature_success";

    // 3. Server-side Payment Verification
    const verifyRes = await fetch(`/api/checkout/verify?session_id=${STATE.sessionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_id: orderData.order_id,
        razorpay_order_id: orderData.razorpay_order_id,
        razorpay_payment_id: mockPaymentId,
        razorpay_signature: mockSignature
      })
    });

    const verifyData = await verifyRes.json();
    if (!verifyRes.ok) throw new Error(verifyData.detail || "Payment verification failed");

    // Capture items for the PhonePe receipt screen before clearing cart
    const purchasedItems = STATE.cart && STATE.cart.items ? [...STATE.cart.items] : [];
    const paidAmount = orderData.amount || (STATE.cart ? STATE.cart.total : 0);

    // Success flow: Reset active cart
    STATE.cartId = null;
    localStorage.removeItem("smartcart_active_cart_id");
    STATE.cart = null;

    renderEmptyCartView();
    updateCartUI(null);
    const chk = document.getElementById("chkUserConfirm");
    if (chk) chk.checked = false;

    // Show order receipt confirmation in chat
    appendChatBubble("assistant", `🎉 **Payment Verified & Order Confirmed!**\n- **Order ID:** \`${verifyData.order_id}\`\n- **Payment ID:** \`${verifyData.razorpay_payment_id}\`\n- **Amount:** ₹${paidAmount.toLocaleString("en-IN")}\n- **Status:** **PAID**\nYour products are being packed!`);

    // Launch Full-Screen PhonePe / UPI Success Modal with chime sound & confetti
    triggerPhonePeSuccess(paidAmount, verifyData.order_id, verifyData.razorpay_payment_id || mockPaymentId, purchasedItems);

  } catch (err) {
    showToast(`❌ Checkout Error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "🔒 Pay with Razorpay Test Mode";
  }
}

// ==========================================
// 5. MERCHANT ANALYTICS & AUDIT TRAIL
// ==========================================

async function loadAnalytics() {
  try {
    const res = await fetch("/api/analytics");
    if (!res.ok) return;
    const m = await res.json();

    document.getElementById("kpiConversations").textContent = m.total_conversations;
    document.getElementById("kpiCarts").textContent = m.carts_created;
    document.getElementById("kpiPaidOrders").textContent = m.successful_test_payments;
    document.getElementById("kpiCrossSellRate").textContent = `${m.cross_sell_acceptance_rate_pct}%`;
    document.getElementById("kpiCrossSellCount").textContent = `${m.cross_sell_accepted}/${m.cross_sell_impressions} accepted`;
    
    document.getElementById("kpiAvgCart").textContent = `₹${m.average_cart_value.toLocaleString("en-IN")}`;
    document.getElementById("kpiTotalRevenue").textContent = `₹${m.total_revenue.toLocaleString("en-IN")}`;

    // Funnel calculations: Sync dynamically with SQLite queries & top KPI cards
    const totalConvs = Math.max(1, m.total_conversations || 1);
    const cartsCreated = m.carts_created || 0;
    const checkoutAttempts = m.checkout_attempts || cartsCreated || 1;
    const paidOrders = m.successful_test_payments || 0;

    const cartRate = Math.min(100, Math.round((cartsCreated / totalConvs) * 100));
    const checkoutRate = Math.min(100, Math.round((checkoutAttempts / Math.max(1, cartsCreated)) * 100));
    const payRate = Math.min(100, Math.round((paidOrders / Math.max(1, checkoutAttempts)) * 100));

    const funnelCartEl = document.getElementById("funnelCartRate");
    const barCartEl = document.getElementById("barCart");
    if (funnelCartEl && barCartEl) {
      funnelCartEl.textContent = `${cartsCreated}/${totalConvs} (${cartRate}%)`;
      barCartEl.style.width = `${cartRate}%`;
    }

    const funnelCheckoutEl = document.getElementById("funnelCheckoutRate");
    const barCheckoutEl = document.getElementById("barCheckout");
    if (funnelCheckoutEl && barCheckoutEl) {
      funnelCheckoutEl.textContent = `${checkoutAttempts}/${Math.max(1, cartsCreated)} (${checkoutRate}%)`;
      barCheckoutEl.style.width = `${checkoutRate}%`;
    }

    const funnelPayEl = document.getElementById("funnelPayRate");
    const barPayEl = document.getElementById("barPay");
    if (funnelPayEl && barPayEl) {
      funnelPayEl.textContent = `${paidOrders}/${Math.max(1, checkoutAttempts)} (${payRate}%)`;
      barPayEl.style.width = `${payRate}%`;
    }

  } catch (err) {
    console.error("Error loading analytics:", err);
  }
}

function formatAuditSummary(l) {
  const action = l.action || "";
  const inp = l.input_data || {};
  const out = l.output_data || {};

  let pillIcon = "🔍";
  let pillClass = "audit-intent";
  let text = "";

  if (action.includes("INTENT") || action.includes("CHAT") || action.includes("SEARCH")) {
    pillIcon = "🎯";
    pillClass = "audit-intent";
    const intentName = out.intent || inp.intent || (inp.message ? "Product Search" : "Intent Extraction");
    const budgetVal = out.budget || inp.budget;
    const budgetStr = budgetVal ? ` • Budget: ₹${Number(budgetVal).toLocaleString("en-IN")}` : "";
    const recCount = out.recommendations ? out.recommendations.length : (out.recommendations_count || (out.matched_count || 0));
    const matchesStr = recCount ? ` → ${recCount} Matched ✓` : "";
    text = `Intent: ${escapeHtml(intentName)}${budgetStr}${matchesStr}`;
  } else if (action.includes("CART") || action.includes("ITEM")) {
    pillIcon = "🛒";
    pillClass = "audit-cart";
    const prodName = inp.product_name || (inp.product_id ? `Product ${inp.product_id}` : (out.items && out.items.length ? `${out.items.length} items` : "Cart updated"));
    const totalStr = out.total ? ` (Total: ₹${Number(out.total).toLocaleString("en-IN")})` : "";
    text = `Cart Event: ${escapeHtml(prodName)}${totalStr}`;
  } else if (action.includes("CHECKOUT")) {
    pillIcon = "💳";
    pillClass = "audit-pay";
    const ordId = out.order_id || inp.order_id || "Order Initialized";
    const amtStr = out.amount ? ` • ₹${(Number(out.amount) / 100).toLocaleString("en-IN")}` : "";
    text = `Checkout Initiated: ${escapeHtml(ordId)}${amtStr} [Gate Verified ✓]`;
  } else if (action.includes("PAYMENT") || action.includes("PAID") || action.includes("SUCCESS")) {
    pillIcon = "🎉";
    pillClass = "audit-success";
    const payId = out.razorpay_payment_id || inp.razorpay_payment_id || "pay_verified";
    text = `Verified Payment: ${escapeHtml(payId)} (PAID ✓)`;
  } else if (action.includes("CATALOG") || action.includes("UPLOAD")) {
    pillIcon = "📦";
    pillClass = "audit-catalog";
    const count = out.valid_count || out.total_products || 15;
    text = `Catalog Ingest: ${count} products imported & verified`;
  } else {
    pillIcon = "🛡️";
    pillClass = "audit-intent";
    text = `${action}: Processed safely`;
  }

  const logId = `rawLog_${l.id}`;
  const rawJson = JSON.stringify({ action: l.action, input: inp, output: out }, null, 2);

  return `
    <div style="display:flex; flex-direction:column; gap:0.35rem;">
      <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
        <span class="audit-summary-pill ${pillClass}">
          ${pillIcon} ${text}
        </span>
        <button class="btn-raw-json" onclick="toggleAuditJson('${logId}')">
          View Raw JSON ▾
        </button>
      </div>
      <pre id="${logId}" class="raw-json-viewer">${escapeHtml(rawJson)}</pre>
    </div>
  `;
}

function toggleAuditJson(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle("open");
}

async function loadAuditLogs() {
  try {
    const res = await fetch("/api/analytics/audit-logs?limit=30");
    if (!res.ok) return;
    const logs = await res.json();

    const tbody = document.getElementById("auditLogsTableBody");
    if (!tbody) return;
    if (!logs || logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No audit events recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs.map(l => `
      <tr>
        <td><span style="font-family:monospace; font-size:0.75rem;">#${l.id}</span></td>
        <td style="font-size:0.75rem; color:var(--text-muted); white-space:nowrap;">${formatTimestamp(l.timestamp)}</td>
        <td><span style="font-size:0.75rem; font-family:monospace;">${escapeHtml(l.session_id)}</span></td>
        <td><span class="badge ${getActionBadgeClass(l.action)}">${escapeHtml(l.action)}</span></td>
        <td>
          ${formatAuditSummary(l)}
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Error loading audit logs:", err);
  }
}

function getActionBadgeClass(action) {
  if (action.includes("SUCCESS") || action.includes("UPLOAD")) return "badge-success";
  if (action.includes("FAILED") || action.includes("REJECTED")) return "badge-danger";
  if (action.includes("PAYMENT") || action.includes("CHECKOUT")) return "badge-warning";
  return "badge-primary";
}

function formatTimestamp(iso) {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return iso;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Initial Boot
document.addEventListener("DOMContentLoaded", () => {
  switchPersona("customer");
  switchTab("chat");
  fetchCatalog();
  loadCartView();
  updateBudgetTracker();
});

// ==========================================
// 6. FULL-SCREEN PHONEPE SUCCESS & AUDIO CHIME
// ==========================================

function playPhonePeChime() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const now = ctx.currentTime;

    // Harmonic UPI chime sequence (G4 -> C5 -> E5 -> G5)
    const tones = [
      { freq: 392.00, start: 0.0, dur: 0.14 },
      { freq: 523.25, start: 0.10, dur: 0.16 },
      { freq: 659.25, start: 0.20, dur: 0.20 },
      { freq: 783.99, start: 0.32, dur: 0.75 }
    ];

    tones.forEach(t => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(t.freq, now + t.start);

      gain.gain.setValueAtTime(0.25, now + t.start);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + t.start + t.dur);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now + t.start);
      osc.stop(now + t.start + t.dur);
    });
  } catch (err) {
    console.warn("Web Audio error:", err);
  }
}

function startConfetti() {
  const canvas = document.getElementById("confettiCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const particles = [];
  const colors = ["#10b981", "#3b82f6", "#f59e0b", "#ec4899", "#8b5cf6", "#ffffff"];
  for (let i = 0; i < 90; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height * 0.4,
      size: Math.random() * 8 + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      vx: (Math.random() - 0.5) * 5,
      vy: Math.random() * 3 + 2,
      rot: Math.random() * 360,
      vrot: (Math.random() - 0.5) * 10
    });
  }

  let frames = 0;
  function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let alive = false;
    particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.vrot;
      if (p.y < canvas.height) alive = true;

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate((p.rot * Math.PI) / 180);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
      ctx.restore();
    });

    frames++;
    if (alive && frames < 180) {
      requestAnimationFrame(render);
    }
  }
  render();
}

let lastCompletedPayment = null;

function triggerPhonePeSuccess(amount, orderId, paymentId, items) {
  lastCompletedPayment = { amount, orderId, paymentId, items, time: new Date() };

  document.getElementById("successDisplayAmount").textContent = amount.toLocaleString("en-IN", { minimumFractionDigits: 2 });
  document.getElementById("successPaymentId").textContent = paymentId;
  document.getElementById("successOrderId").textContent = orderId;
  document.getElementById("successTimestamp").textContent = new Date().toLocaleString("en-IN", {
    month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit"
  });

  document.getElementById("successItemsCount").textContent = items ? items.length : 0;
  const itemsContainer = document.getElementById("successItemsList");
  if (items && items.length > 0) {
    itemsContainer.innerHTML = items.map(item => `
      <div class="slip-item-entry">
        <span>${item.quantity}x ${escapeHtml(item.name)}</span>
        <strong style="color:var(--text-main);">₹${item.line_total.toLocaleString("en-IN")}</strong>
      </div>
    `).join("");
  } else {
    itemsContainer.innerHTML = `<div style="color:var(--text-muted); font-size:0.75rem;">Instant Checkout</div>`;
  }

  const modal = document.getElementById("paymentSuccessModal");
  modal.classList.add("active");

  playPhonePeChime();
  startConfetti();
}

function closeSuccessModalAndContinue() {
  document.getElementById("paymentSuccessModal").classList.remove("active");
  switchTab("catalog");
}

function copyTransactionId() {
  if (lastCompletedPayment && lastCompletedPayment.paymentId) {
    navigator.clipboard.writeText(lastCompletedPayment.paymentId);
    showToast("📋 Transaction ID copied to clipboard!");
  }
}

function printReceipt() {
  window.print();
}

// ==========================================
// 7. VOICE INPUT / SPEAK TO SHOP
// ==========================================
let recognition = null;
let isListening = false;

function toggleVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    showToast("🎙️ Voice search is best supported in Chrome, Edge, or Safari.");
    return;
  }

  const micBtn = document.getElementById("btnVoiceInput");
  const statusBar = document.getElementById("voiceStatusIndicator");

  if (isListening && recognition) {
    recognition.stop();
    isListening = false;
    micBtn.classList.remove("listening");
    if (statusBar) statusBar.style.display = "none";
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = "en-IN";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    isListening = true;
    micBtn.classList.add("listening");
    if (statusBar) statusBar.style.display = "flex";
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById("chatInput").value = transcript;
    showToast(`🎙️ Recognized: "${transcript}"`);
    handleChatSubmit(new Event("submit"));
  };

  recognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    isListening = false;
    micBtn.classList.remove("listening");
    if (statusBar) statusBar.style.display = "none";
  };

  recognition.onend = () => {
    isListening = false;
    micBtn.classList.remove("listening");
    if (statusBar) statusBar.style.display = "none";
  };

  recognition.start();
}
