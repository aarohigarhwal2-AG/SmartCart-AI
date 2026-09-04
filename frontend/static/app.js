// SmartCart AI Frontend Application Logic

const STATE = {
  sessionId: "session_" + Math.random().toString(36).substring(2, 9),
  cartId: localStorage.getItem("smartcart_active_cart_id") || null,
  activeTab: "catalog",
  products: [],
  cart: null
};

// Toast notification helper
function showToast(msg, duration = 3000) {
  const toast = document.getElementById("appToast");
  toast.textContent = msg;
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, duration);
}

// Tab Switching
function switchTab(tabName) {
  STATE.activeTab = tabName;
  document.querySelectorAll(".nav-btn").forEach((btn, idx) => {
    btn.classList.remove("active");
  });
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

  const targetPane = document.getElementById(`pane-${tabName}`);
  if (targetPane) targetPane.classList.add("active");

  const tabIndex = ["catalog", "chat", "cart", "analytics"].indexOf(tabName);
  const btns = document.querySelectorAll(".nav-btn");
  if (btns[tabIndex]) btns[tabIndex].classList.add("active");

  // Refresh tab data
  if (tabName === "catalog") fetchCatalog();
  if (tabName === "cart") loadCartView();
  if (tabName === "analytics") {
    loadAnalytics();
    loadAuditLogs();
  }
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

  document.getElementById("productTotalBadge").textContent = `${total} Products`;
  document.getElementById("statInStock").textContent = inStock;
  document.getElementById("statOutOfStock").textContent = outOfStock;
  document.getElementById("statCategories").textContent = categories;
}

function renderCatalogTable(products) {
  const tbody = document.getElementById("catalogTableBody");
  if (!products || products.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:2rem;">No products found. Upload a CSV or click "Load 15-Item Sample".</td></tr>`;
    return;
  }

  tbody.innerHTML = products.map(p => `
    <tr>
      <td><span style="font-family:monospace; font-weight:600; color:var(--primary);">${p.id}</span></td>
      <td style="font-weight:600;">${escapeHtml(p.name)}</td>
      <td><span class="badge badge-primary">${escapeHtml(p.category)}</span></td>
      <td style="font-size:0.8rem; color:var(--text-muted); max-width:280px;">${escapeHtml(p.description)}</td>
      <td style="font-weight:700; color:var(--text-main);">₹${p.price.toLocaleString("en-IN")}</td>
      <td>
        ${p.stock > 0 
          ? `<span class="badge badge-success">In Stock (${p.stock})</span>` 
          : `<span class="badge badge-danger">Out of Stock (0)</span>`}
      </td>
      <td style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(p.tags)}</td>
    </tr>
  `).join("");
}

function filterCatalogTable() {
  const query = (document.getElementById("catalogSearchInput").value || "").toLowerCase();
  const inStockOnly = document.getElementById("filterInStockOnly").checked;

  const filtered = STATE.products.filter(p => {
    const matchesQuery = p.name.toLowerCase().includes(query) ||
                         p.description.toLowerCase().includes(query) ||
                         p.category.toLowerCase().includes(query) ||
                         p.tags.toLowerCase().includes(query);
    const matchesStock = inStockOnly ? p.stock > 0 : true;
    return matchesQuery && matchesStock;
  });

  renderCatalogTable(filtered);
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
  alertBox.textContent = "Loading real-world Amazon/Flipkart sourced catalog...";

  try {
    const res = await fetch("/api/catalog/load-real", { method: "POST" });
    const data = await res.json();
    
    alertBox.style.background = "#dcfce7";
    alertBox.style.color = "#166534";
    alertBox.textContent = `✅ Loaded ${data.valid_count} real-world products (Amazon.in / Flipkart)!`;

    STATE.products = data.products;
    renderCatalogTable(STATE.products);
    updateCatalogStats(STATE.products);
    showToast("Real-world catalog loaded!");
  } catch (err) {
    alertBox.style.background = "#fee2e2";
    alertBox.style.color = "#991b1b";
    alertBox.textContent = "Failed to load real catalog.";
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
    const budgetStr = data.intent.budget ? ` • Budget: ₹${data.intent.budget.toLocaleString("en-IN")}` : "";
    intentInfo = `<div class="intent-tag-pill">🎯 Intent: ${data.intent.intent}${budgetStr}</div>`;
  }

  let html = `<div>${escapeHtml(data.reply).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</div>${intentInfo}`;

  // Primary Recommendations
  if (data.recommendations && data.recommendations.length > 0) {
    html += `<div class="rec-cards-list">`;
    data.recommendations.forEach(rec => {
      const p = rec.product;
      const cardClass = rec.is_upsell ? "rec-card upsell" : "rec-card";
      const tagText = rec.is_upsell ? "⭐ UPSELL UPGRADE" : "✅ RECOMMENDED";
      
      html += `
        <div class="${cardClass}">
          <div class="rec-info">
            <div style="font-size:0.65rem; font-weight:700; color:var(--primary);">${tagText}</div>
            <h4>${escapeHtml(p.name)}</h4>
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
      html += `
        <div class="rec-card cross-sell">
          <div class="rec-info">
            <div style="font-size:0.65rem; font-weight:700; color:var(--secondary);">💡 COMPLEMENTARY ADD-ON</div>
            <h4>${escapeHtml(p.name)}</h4>
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
// 3. CART & CHECKOUT FUNCTIONS
// ==========================================

async function addItemToCart(productId, productName) {
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
      showToast(`⚠️ ${data.detail || "Could not add item."}`);
      return;
    }

    STATE.cart = data;
    updateCartUI(data);
    showToast(`Added '${productName}' to cart!`);
  } catch (err) {
    showToast(`⚠️ Error: ${err.message}`);
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

function updateCartUI(cart) {
  const count = cart ? cart.item_count : 0;
  document.getElementById("cartBadgeCount").textContent = count;
  document.getElementById("cartTotalItems").textContent = count;

  // Render Mini Cart in chat sidebar
  const mini = document.getElementById("miniCartContent");
  if (!cart || cart.items.length === 0) {
    mini.innerHTML = `<p style="font-size:0.85rem; color:var(--text-muted); text-align:center; padding:1.5rem 0;">Your cart is empty.</p>`;
    return;
  }

  mini.innerHTML = `
    <div style="display:flex; flex-direction:column; gap:0.5rem;">
      ${cart.items.map(item => `
        <div style="display:flex; justify-content:space-between; font-size:0.85rem;">
          <span>${item.quantity}x ${escapeHtml(item.name)}</span>
          <span style="font-weight:600;">₹${item.line_total.toLocaleString("en-IN")}</span>
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
  document.getElementById("cartItemsList").innerHTML = `
    <div style="text-align:center; padding:3rem 1rem; color:var(--text-muted);">
      <p style="font-size:2rem; margin-bottom:0.5rem;">🛒</p>
      <p style="font-weight:600; font-size:1rem;">Your cart is empty</p>
      <p style="font-size:0.8rem; margin-top:0.25rem;">Chat with the assistant or browse catalog to add products.</p>
      <button class="btn btn-primary btn-sm" style="margin-top:1rem;" onclick="switchTab('chat')">Start Shopping →</button>
    </div>
  `;
  document.getElementById("summarySubtotal").textContent = "₹0.00";
  document.getElementById("summaryTotal").textContent = "₹0.00";
  document.getElementById("btnProceedCheckout").disabled = true;
}

function renderFullCartView(cart) {
  if (!cart.items || cart.items.length === 0) {
    renderEmptyCartView();
    return;
  }

  const itemsHtml = cart.items.map(item => `
    <div style="display:flex; justify-content:space-between; align-items:center; padding:1rem 0; border-bottom:1px solid var(--border);">
      <div>
        <h4 style="font-size:0.95rem; font-weight:600;">${escapeHtml(item.name)}</h4>
        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.15rem;">Unit Price: ₹${item.unit_price.toLocaleString("en-IN")} • Category: ${escapeHtml(item.category)}</div>
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
  const confirmed = document.getElementById("chkUserConfirm").checked;
  const hasItems = STATE.cart && STATE.cart.items && STATE.cart.items.length > 0;
  document.getElementById("btnProceedCheckout").disabled = !(confirmed && hasItems);
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

    // Success flow: Reset active cart and notify user
    showToast("🎉 Payment verified successfully! Order completed.");
    STATE.cartId = null;
    localStorage.removeItem("smartcart_active_cart_id");
    STATE.cart = null;

    renderEmptyCartView();
    updateCartUI(null);
    document.getElementById("chkUserConfirm").checked = false;

    // Show order receipt confirmation
    appendChatBubble("assistant", `🎉 **Payment Verified & Order Confirmed!**\n- **Order ID:** \`${verifyData.order_id}\`\n- **Payment ID:** \`${verifyData.razorpay_payment_id}\`\n- **Status:** **PAID**\nYour products are being prepared for dispatch!`);
    
    // Switch to Analytics to view updated metrics
    setTimeout(() => {
      switchTab("analytics");
    }, 1200);

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

    // Funnel calculations
    const recRate = Math.min(100, Math.round((m.product_search_requests / Math.max(1, m.total_conversations)) * 100));
    const cartRate = Math.min(100, Math.round((m.carts_created / Math.max(1, m.product_search_requests)) * 100));
    const payRate = Math.min(100, Math.round((m.successful_test_payments / Math.max(1, m.checkout_attempts)) * 100));

    document.getElementById("funnelRecRate").textContent = `${recRate}%`;
    document.getElementById("barRec").style.width = `${recRate}%`;
    
    document.getElementById("funnelCartRate").textContent = `${cartRate}%`;
    document.getElementById("barCart").style.width = `${cartRate}%`;

    document.getElementById("funnelPayRate").textContent = `${payRate}%`;
    document.getElementById("barPay").style.width = `${payRate}%`;

  } catch (err) {
    console.error("Error loading analytics:", err);
  }
}

async function loadAuditLogs() {
  try {
    const res = await fetch("/api/analytics/audit-logs?limit=30");
    if (!res.ok) return;
    const logs = await res.json();

    const tbody = document.getElementById("auditLogsTableBody");
    if (!logs || logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No audit events recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs.map(l => `
      <tr>
        <td><span style="font-family:monospace; font-size:0.75rem;">#${l.id}</span></td>
        <td style="font-size:0.75rem; color:var(--text-muted); white-space:nowrap;">${formatTimestamp(l.timestamp)}</td>
        <td><span style="font-size:0.75rem; font-family:monospace;">${escapeHtml(l.session_id)}</span></td>
        <td><span class="badge ${getActionBadgeClass(l.action)}">${escapeHtml(l.action)}</span></td>
        <td style="font-size:0.75rem; font-family:monospace; max-width:240px; overflow:hidden; text-overflow:ellipsis;">
          ${l.input_data ? escapeHtml(JSON.stringify(l.input_data)) : "-"}
        </td>
        <td style="font-size:0.75rem; font-family:monospace; max-width:240px; overflow:hidden; text-overflow:ellipsis;">
          ${l.output_data ? escapeHtml(JSON.stringify(l.output_data)) : "-"}
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
  fetchCatalog();
  loadCartView();
});
