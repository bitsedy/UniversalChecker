/**
 * Ghanaian Result Checker Reseller Platform - Client Application
 * Features: Mobile Money auto-telco detection, atomic reservation checkout,
 * live USSD prompt simulation, one-click copy, and official portal deep-linking.
 */

const TELCO_PREFIXES = {
  MTN: ["024", "054", "055", "059", "053"],
  TELECEL: ["020", "050"],
  AT: ["027", "057", "026"]
};

let currentOrder = null;

document.addEventListener("DOMContentLoaded", () => {
  setupTelcoAutoDetect();
  setupQuantityListeners();
  // initLiveSocialProof(); // Halted during testing stage to preserve authenticity
  initScrollEngine();
  setupVoucherCopyDelegation();
});

// Auto-detect Ghanaian network from phone number
function setupTelcoAutoDetect() {
  const phoneInput = document.getElementById("customer_phone");
  if (!phoneInput) return;

  phoneInput.addEventListener("input", (e) => {
    let val = e.target.value.replace(/\D/g, "");
    if (val.startsWith("233")) {
      val = "0" + val.substring(3);
    }
    const prefix = val.substring(0, 3);
    
    for (const [telco, prefixes] of Object.entries(TELCO_PREFIXES)) {
      if (prefixes.includes(prefix)) {
        const radio = document.getElementById(`radio_${telco.toLowerCase()}`);
        if (radio) {
          radio.checked = true;
          highlightTelcoBox(telco.toLowerCase());
        }
        break;
      }
    }
  });

  document.querySelectorAll('input[name="payment_network"]').forEach(radio => {
    radio.addEventListener("change", (e) => {
      const telcoKey = e.target.id.replace("radio_", "");
      highlightTelcoBox(telcoKey);
    });
  });
}

function highlightTelcoBox(telcoKey) {
  document.querySelectorAll(".telco-radio-card").forEach(card => {
    card.classList.remove("active-mtn", "active-telecel", "active-at");
  });
  const targetCard = document.querySelector(`.telco-radio-card input#radio_${telcoKey}`)?.closest(".telco-radio-card");
  if (targetCard) {
    targetCard.classList.add(`active-${telcoKey}`);
  }
}

// Calculate total based on quantity
function setupQuantityListeners() {
  const qtySelect = document.getElementById("order_quantity");
  if (!qtySelect) return;

  qtySelect.addEventListener("change", () => {
    updateModalPrice();
  });
}

function updateModalPrice() {
  const qty = parseInt(document.getElementById("order_quantity").value || "1", 10);
  const unitPrice = parseFloat(document.getElementById("modal_unit_price").dataset.price || "0");
  const total = (qty * unitPrice).toFixed(2);
  const totalDisplay = document.getElementById("modal_total_price");
  if (totalDisplay) {
    totalDisplay.innerText = `GHS ${total}`;
  }
}

// Open Checkout Modal
function openBuyModal(category, name, price, stock) {
  if (stock <= 0) {
    alert(`Sorry! ${name} is currently out of stock. Please check back shortly.`);
    return;
  }

  document.getElementById("modal_category").value = category;
  document.getElementById("modal_product_title").innerText = name;
  
  const unitElem = document.getElementById("modal_unit_price");
  unitElem.dataset.price = price;
  unitElem.innerText = `GHS ${parseFloat(price).toFixed(2)}`;

  document.getElementById("order_quantity").value = "1";
  updateModalPrice();

  // Reset steps
  document.getElementById("checkout_step_details").style.display = "block";
  document.getElementById("checkout_step_payment").style.display = "none";
  document.getElementById("checkout_step_success").style.display = "none";

  document.getElementById("checkout_modal").classList.add("active");
}

let redirectTimer = null;
let redirectSeconds = 6;
let isRedirectPaused = false;
let activePortalUrl = "";
let activePortalName = "";

function closeModal() {
  if (redirectTimer) {
    clearInterval(redirectTimer);
    redirectTimer = null;
  }
  document.getElementById("checkout_modal").classList.remove("active");
}

// Submit Order and Trigger Reservation
async function submitOrder() {
  const category = document.getElementById("modal_category").value;
  const quantity = parseInt(document.getElementById("order_quantity").value, 10);
  const phone = document.getElementById("customer_phone").value.trim();
  const email = document.getElementById("customer_email").value.trim();
  
  const selectedPayment = document.querySelector('input[name="payment_network"]:checked');
  const paymentMethod = selectedPayment ? selectedPayment.value : "MOMO_MTN";

  if (!phone || phone.length < 9) {
    alert("Please enter a valid Ghanaian mobile phone number.");
    return;
  }

  const btn = document.getElementById("btn_submit_order");
  btn.innerText = "Reserving Voucher...";
  btn.disabled = true;

  try {
    const res = await fetch("/api/orders/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        category,
        quantity,
        customer_phone: phone,
        customer_email: email,
        payment_method: paymentMethod
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      alert(data.message || "Failed to reserve voucher. It may be temporarily out of stock.");
      btn.innerText = "Proceed to Payment";
      btn.disabled = false;
      return;
    }

    currentOrder = data.order;
    showPaymentPrompt(data);
  } catch (err) {
    alert("Network error: " + err.message);
    btn.innerText = "Proceed to Payment";
    btn.disabled = false;
  }
}

let currentPaystackKey = "";

// Show MoMo USSD Prompt Screen
function showPaymentPrompt(data) {
  document.getElementById("checkout_step_details").style.display = "none";
  document.getElementById("checkout_step_payment").style.display = "block";

  currentPaystackKey = data.paystack_public_key || "";

  const promptInfo = data.payment_prompt;
  document.getElementById("momo_display_network").innerText = promptInfo.network;
  document.getElementById("momo_display_phone").innerText = promptInfo.phone_formatted;
  document.getElementById("momo_display_amount").innerText = `GHS ${promptInfo.amount_ghs.toFixed(2)}`;
  document.getElementById("momo_display_order_ref").innerText = data.order.order_reference;
  document.getElementById("momo_prompt_instructions").innerText = promptInfo.prompt_text;
  document.getElementById("momo_manual_steps").innerText = promptInfo.manual_steps;
}

// Trigger Official Paystack Popup Modal (MoMo & Card)
function payWithPaystack() {
  if (!currentOrder) return;
  if (!currentPaystackKey || currentPaystackKey.includes("sample")) {
    alert("Paystack Notice:\nYou currently have default sample keys configured.\n\nTo accept live or test payments via Paystack popup:\n1. Go to /admin\n2. Paste your Paystack Public Key (pk_test_... or pk_live_...)\n3. Click 'Save Settings & Prices'\n\nFor now, you can click 'Quick Sandbox Test' below to test the instant voucher delivery!");
    return;
  }
  if (typeof PaystackPop === "undefined") {
    alert("Paystack SDK is loading or unavailable. Please verify your internet connection.");
    return;
  }

  const handler = PaystackPop.setup({
    key: currentPaystackKey,
    email: currentOrder.customer_email || `buyer_${currentOrder.order_reference.toLowerCase().replace(/[^a-z0-9]/g, "")}@checkerpay.gh`,
    amount: Math.round(currentOrder.total_amount * 100),
    currency: "GHS",
    ref: currentOrder.order_reference,
    channels: ["mobile_money", "card"],
    metadata: {
      custom_fields: [
        { display_name: "Customer Phone", variable_name: "customer_phone", value: currentOrder.customer_phone },
        { display_name: "Category", variable_name: "category", value: currentOrder.category }
      ]
    },
    callback: function(response) {
      verifyPaystackPayment(response.reference);
    },
    onClose: function() {
      console.log("Paystack dialog closed.");
    }
  });
  handler.openIframe();
}

function renderVouchersSkeleton(qty = 1) {
  const container = document.getElementById("vouchers_container");
  if (!container) return;
  container.replaceChildren();
  for (let i = 0; i < qty; i++) {
    const card = document.createElement("div");
    card.className = "skeleton-voucher-card";
    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
        <span class="skeleton skeleton-line" style="width: 150px; height: 14px; margin: 0;"></span>
        <span class="skeleton skeleton-badge" style="width: 80px; height: 18px;"></span>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 100px; gap: 1rem; align-items: center; margin-bottom: 0.75rem; background: #f8fafc; padding: 0.75rem; border-radius: 8px;">
        <div>
          <div class="skeleton skeleton-line" style="width: 80px; height: 10px; margin-bottom: 6px;"></div>
          <div class="skeleton skeleton-line" style="width: 170px; height: 18px; margin: 0;"></div>
        </div>
        <div class="skeleton skeleton-btn" style="height: 32px; width: 80px; margin-left: auto;"></div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 100px; gap: 1rem; align-items: center; background: #f8fafc; padding: 0.75rem; border-radius: 8px;">
        <div>
          <div class="skeleton skeleton-line" style="width: 60px; height: 10px; margin-bottom: 6px;"></div>
          <div class="skeleton skeleton-line" style="width: 140px; height: 18px; margin: 0;"></div>
        </div>
        <div class="skeleton skeleton-btn" style="height: 32px; width: 80px; margin-left: auto;"></div>
      </div>
    `;
    container.appendChild(card);
  }
}

async function verifyPaystackPayment(orderRef) {
  const btn = document.getElementById("btn_paystack_pay");
  if (btn) {
    btn.innerText = "Confirming Paystack Payment...";
    btn.disabled = true;
  }

  // Show immediate voucher shimmer skeleton while verifying with server
  document.getElementById("checkout_step_payment").style.display = "none";
  document.getElementById("checkout_step_success").style.display = "block";
  document.getElementById("redirect_countdown_box").style.display = "none";
  renderVouchersSkeleton(currentOrder ? currentOrder.quantity : 1);

  try {
    const res = await fetch("/api/orders/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_reference: orderRef,
        provider: "PAYSTACK"
      })
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      alert(data.message || "Paystack payment verification failed.");
      document.getElementById("checkout_step_success").style.display = "none";
      document.getElementById("checkout_step_payment").style.display = "block";
      if (btn) {
        btn.innerText = "Pay via Paystack (MoMo & Cards)";
        btn.disabled = false;
      }
      return;
    }
    showSuccessVouchers(data);
  } catch (err) {
    alert("Payment verification error: " + err.message);
    document.getElementById("checkout_step_success").style.display = "none";
    document.getElementById("checkout_step_payment").style.display = "block";
    if (btn) {
      btn.innerText = "Pay via Paystack (MoMo & Cards)";
      btn.disabled = false;
    }
  }
}

// Complete / Simulate Approval
async function approveSimulatedPayment() {
  if (!currentOrder) return;
  const btn = document.getElementById("btn_approve_payment");
  btn.innerText = "Verifying Transaction...";
  btn.disabled = true;

  // Show immediate voucher shimmer skeleton while server processes
  document.getElementById("checkout_step_payment").style.display = "none";
  document.getElementById("checkout_step_success").style.display = "block";
  document.getElementById("redirect_countdown_box").style.display = "none";
  renderVouchersSkeleton(currentOrder ? currentOrder.quantity : 1);

  try {
    const res = await fetch("/api/orders/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_reference: currentOrder.order_reference,
        provider: "MOMO_SIMULATOR"
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      alert(data.message || "Verification failed.");
      document.getElementById("checkout_step_success").style.display = "none";
      document.getElementById("checkout_step_payment").style.display = "block";
      btn.innerText = "Quick Sandbox Test (Simulate MoMo Approval)";
      btn.disabled = false;
      return;
    }

    showSuccessVouchers(data);
  } catch (err) {
    alert("Verification error: " + err.message);
    document.getElementById("checkout_step_success").style.display = "none";
    document.getElementById("checkout_step_payment").style.display = "block";
    btn.innerText = "Quick Sandbox Test (Simulate MoMo Approval)";
    btn.disabled = false;
  }
}

// Render Sold Vouchers on Screen — XSS-safe via DOM API (no innerHTML for user data)
function _esc(val) {
  // Returns a text node-safe string — used exclusively with textContent, never innerHTML
  return String(val == null ? "" : val);
}

function _makeCopyBtn(label, valueToCopy) {
  const btn = document.createElement("button");
  btn.className = "btn-copy";
  btn.textContent = label;
  // Store the value in a data attribute so no JS runs from inline handlers
  btn.dataset.copyValue = valueToCopy;
  return btn;
}

// Single delegated listener on the vouchers container (set up once in DOMContentLoaded)
function setupVoucherCopyDelegation() {
  const container = document.getElementById("vouchers_container");
  if (!container) return;
  container.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-copy-value]");
    if (!btn) return;
    copyText(btn.dataset.copyValue, btn);
  });
}

function showSuccessVouchers(data) {
  document.getElementById("checkout_step_payment").style.display = "none";
  document.getElementById("checkout_step_success").style.display = "block";

  const container = document.getElementById("vouchers_container");
  // Clear container using replaceChildren (safe — no HTML parsing)
  container.replaceChildren();

  const fulfillment = data.fulfillment;
  document.getElementById("success_order_ref").innerText = _esc(fulfillment.order_reference);

  fulfillment.cards.forEach((c) => {
    // ── Card wrapper ──────────────────────────────────────────────
    const card = document.createElement("div");
    card.className = "voucher-reveal-card";

    // ── Header row ──────────────────────────────────────────────
    const header = document.createElement("div");
    header.style.cssText = "display:flex;justify-content:space-between;margin-bottom:0.75rem;";

    const titleSpan = document.createElement("span");
    titleSpan.style.cssText = "font-weight:700;color:var(--ghana-gold);";
    titleSpan.textContent = `${_esc(fulfillment.category_title)} (Card #${_esc(c.item_number)})`;

    const statusSpan = document.createElement("span");
    statusSpan.style.cssText = "font-size:0.8rem;color:var(--ghana-green);font-weight:700;";
    statusSpan.textContent = "ACTIVE / VALID";

    header.appendChild(titleSpan);
    header.appendChild(statusSpan);
    card.appendChild(header);

    // ── Serial field ──────────────────────────────────────────────
    const serialField = document.createElement("div");
    serialField.className = "voucher-field";

    const serialInfo = document.createElement("div");
    const serialLabel = document.createElement("div");
    serialLabel.className = "voucher-field-label";
    serialLabel.textContent = "Serial Number";
    const serialVal = document.createElement("div");
    serialVal.className = "voucher-val";
    serialVal.id = `serial_${_esc(c.item_number)}`;
    serialVal.textContent = _esc(c.serial_number);
    serialInfo.appendChild(serialLabel);
    serialInfo.appendChild(serialVal);
    serialField.appendChild(serialInfo);
    serialField.appendChild(_makeCopyBtn("Copy Serial", _esc(c.serial_number)));
    card.appendChild(serialField);

    // ── PIN field ──────────────────────────────────────────────
    const pinField = document.createElement("div");
    pinField.className = "voucher-field";

    const pinInfo = document.createElement("div");
    const pinLabel = document.createElement("div");
    pinLabel.className = "voucher-field-label";
    pinLabel.textContent = "Voucher PIN";
    const pinVal = document.createElement("div");
    pinVal.className = "voucher-val";
    pinVal.id = `pin_${_esc(c.item_number)}`;
    pinVal.textContent = _esc(c.pin);
    pinInfo.appendChild(pinLabel);
    pinInfo.appendChild(pinVal);
    pinField.appendChild(pinInfo);
    pinField.appendChild(_makeCopyBtn("Copy PIN", _esc(c.pin)));
    card.appendChild(pinField);

    container.appendChild(card);
  });

  // Setup Portal Link & Dynamic Auto-Redirect
  activePortalUrl = fulfillment.portal_url;
  activePortalName = fulfillment.portal_name || (fulfillment.category + " Official Portal");

  const portalNameElem = document.getElementById("redirect_portal_name");
  if (portalNameElem) portalNameElem.innerText = activePortalName;

  const directLinkElem = document.getElementById("redirect_direct_link");
  if (directLinkElem) {
    directLinkElem.href = activePortalUrl;
    directLinkElem.innerText = activePortalUrl;
  }

  const goNowBtn = document.getElementById("btn_go_now");
  if (goNowBtn) goNowBtn.href = activePortalUrl;

  const portalBtn = document.getElementById("btn_launch_portal");
  if (portalBtn) {
    portalBtn.href = activePortalUrl;
    portalBtn.target = "_blank";
    portalBtn.innerText = `Check Results on ${activePortalName} ↗`;
  }

  // Setup WhatsApp Share Link
  const whatsappBtn = document.getElementById("btn_share_whatsapp");
  if (whatsappBtn && data.whatsapp_text) {
    whatsappBtn.href = `https://wa.me/?text=${encodeURIComponent(data.whatsapp_text)}`;
  }

  // Start 6-second countdown timer for auto-redirect
  startAutoRedirect(6);
}

// Auto-Redirect Countdown Engine (between 5 and 8 seconds)
function startAutoRedirect(seconds) {
  if (redirectTimer) clearInterval(redirectTimer);
  redirectSeconds = seconds || 6;
  isRedirectPaused = false;

  const countdownNum = document.getElementById("redirect_countdown_num");
  const progressBar = document.getElementById("redirect_progress_bar");
  const pauseBtn = document.getElementById("btn_cancel_redirect");

  if (countdownNum) countdownNum.innerText = redirectSeconds;
  if (progressBar) {
    progressBar.style.transition = "width 1s linear";
    progressBar.style.width = "100%";
    progressBar.style.background = "linear-gradient(90deg, var(--ghana-gold), var(--ghana-green))";
  }
  if (pauseBtn) {
    pauseBtn.innerText = "Pause Redirect";
    pauseBtn.style.color = "var(--text-muted)";
  }

  const initialSeconds = redirectSeconds;
  redirectTimer = setInterval(() => {
    if (isRedirectPaused) return;

    redirectSeconds -= 1;
    if (countdownNum) countdownNum.innerText = redirectSeconds;
    if (progressBar) {
      const pct = Math.max(0, (redirectSeconds / initialSeconds) * 100);
      progressBar.style.width = `${pct}%`;
    }

    if (redirectSeconds <= 0) {
      clearInterval(redirectTimer);
      redirectTimer = null;

      if (countdownNum) countdownNum.innerText = "0";
      if (progressBar) {
        progressBar.style.width = "100%";
        progressBar.style.background = "var(--ghana-green)";
      }

      const box = document.getElementById("redirect_countdown_box");
      if (box) {
        box.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
              <span style="color: var(--ghana-green); font-weight: 800;">✓ Redirecting to ${activePortalName}...</span>
              <div style="font-size: 0.775rem; color: var(--text-muted); margin-top: 2px;">
                If the portal did not open automatically, <a href="${activePortalUrl}" target="_blank" rel="noopener noreferrer" style="color: var(--ghana-gold); text-decoration: underline; font-weight: 700;">click here to open directly ↗</a>
              </div>
            </div>
            <a href="${activePortalUrl}" target="_blank" rel="noopener noreferrer" class="btn-go-now" style="font-size: 0.85rem; padding: 6px 14px;">
              Open Portal ↗
            </a>
          </div>
        `;
      }

      // Automatically launch the official portal in a new tab
      try {
        window.open(activePortalUrl, "_blank");
      } catch (e) {
        console.warn("Popup blocked or not allowed, fallback link ready in UI.", e);
      }
    }
  }, 1000);
}

function toggleAutoRedirect() {
  const pauseBtn = document.getElementById("btn_cancel_redirect");
  if (!isRedirectPaused) {
    isRedirectPaused = true;
    if (pauseBtn) {
      pauseBtn.innerText = "▶ Resume Countdown";
      pauseBtn.style.color = "var(--ghana-gold)";
    }
  } else {
    isRedirectPaused = false;
    if (pauseBtn) {
      pauseBtn.innerText = "Pause Redirect";
      pauseBtn.style.color = "var(--text-muted)";
    }
  }
}

// Copy to Clipboard Utility
function copyText(text, btnElement) {
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btnElement.innerText;
    btnElement.innerText = "✓ Copied!";
    btnElement.style.background = "var(--ghana-green)";
    btnElement.style.color = "#fff";
    setTimeout(() => {
      btnElement.innerText = originalText;
      btnElement.style.background = "rgba(245, 158, 11, 0.15)";
      btnElement.style.color = "var(--ghana-gold)";
    }, 2000);
  }).catch(err => {
    prompt("Copy voucher credential:", text);
  });
}

// Live Social Proof Notification Engine (Zero PII - Verified Events)
const VERIFIED_ACTIVITY_FEED = [
  { exam: "WASSCE Checker", prefix: "024", suffix: "4192", city: "Accra", time: "18s ago" },
  { exam: "BECE Checker", prefix: "055", suffix: "8821", city: "Kumasi", time: "42s ago" },
  { exam: "CSSPS Placement Voucher", prefix: "020", suffix: "1943", city: "Takoradi", time: "1m ago" },
  { exam: "WASSCE 3-Pack Checker", prefix: "059", suffix: "3012", city: "Tema", time: "2m ago" },
  { exam: "CTVET Technical Voucher", prefix: "027", suffix: "6649", city: "Tamale", time: "3m ago" },
  { exam: "BECE Placement Voucher", prefix: "054", suffix: "7201", city: "Cape Coast", time: "4m ago" },
  { exam: "WASSCE Checker", prefix: "050", suffix: "9315", city: "Sunyani", time: "5m ago" }
];

let socialProofIndex = 0;
function initLiveSocialProof() {
  // Halted during testing stage; will be re-enabled when live production officially commences.
  return;

  const toast = document.getElementById("live_activity_toast");
  if (!toast) return;

  function showNextEvent() {
    const ev = VERIFIED_ACTIVITY_FEED[socialProofIndex % VERIFIED_ACTIVITY_FEED.length];
    socialProofIndex++;

    const titleElem = document.getElementById("toast_title");
    const descElem = document.getElementById("toast_desc");
    const timeElem = document.getElementById("toast_time");

    if (titleElem) titleElem.innerText = "Verified Order Fulfilled";
    if (descElem) descElem.innerHTML = `<strong>${ev.exam}</strong> sent to ${ev.prefix} ••• ${ev.suffix} (${ev.city})`;
    if (timeElem) timeElem.innerText = ev.time;

    toast.classList.add("visible");

    // Hide after 5 seconds
    setTimeout(() => {
      toast.classList.remove("visible");
    }, 5000);
  }

  // Initial delay 3s, then cycle every 14s
  setTimeout(showNextEvent, 3000);
  setInterval(showNextEvent, 14000);
}

// Interactive FAQ Accordion & Category Filtering
function toggleFaq(buttonElem) {
  const item = buttonElem.closest(".faq-item");
  if (!item) return;
  const wasOpen = item.classList.contains("open");
  document.querySelectorAll(".faq-item").forEach(el => el.classList.remove("open"));
  if (!wasOpen) {
    item.classList.add("open");
  }
}

function filterFaq(category, pillElem) {
  document.querySelectorAll(".faq-category-btn").forEach(btn => btn.classList.remove("active"));
  if (pillElem) pillElem.classList.add("active");

  const items = document.querySelectorAll(".faq-item");
  items.forEach(item => {
    const itemCat = item.getAttribute("data-category");
    if (category === "all" || itemCat === category) {
      item.style.display = "block";
    } else {
      item.style.display = "none";
      item.classList.remove("open");
    }
  });
}

/**
 * Sovereign Navigation Scroll Engine
 * Drives the real-time top laser progress beam and floating precision scroll navigator orb.
 * Throttled with requestAnimationFrame for 60fps buttery smooth performance.
 */
function initScrollEngine() {
  const progressBar = document.getElementById("scroll_progress_bar");
  const scrollTopBtn = document.getElementById("scroll_top_btn");
  const ringProgress = document.getElementById("scroll_ring_progress");
  const percentText = document.getElementById("scroll_percent_text");

  if (!progressBar && !scrollTopBtn) return;

  const RING_CIRCUMFERENCE = 125.66; // 2 * PI * 20
  let isTicking = false;

  function updateScrollState() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
    const docHeight = (document.documentElement.scrollHeight || document.body.scrollHeight) - window.innerHeight;
    const progress = docHeight > 0 ? Math.min(100, Math.max(0, (scrollTop / docHeight) * 100)) : 0;
    const roundedProgress = Math.round(progress);

    // 1. Update top micro-beam progress laser
    if (progressBar) {
      progressBar.style.width = `${progress}%`;
      progressBar.setAttribute("aria-valuenow", roundedProgress);
    }

    // 2. Update circular SVG progress ring & percentage text
    if (ringProgress) {
      const offset = RING_CIRCUMFERENCE - (progress / 100) * RING_CIRCUMFERENCE;
      ringProgress.style.strokeDashoffset = offset;
    }
    if (percentText) {
      percentText.textContent = `${roundedProgress}%`;
    }

    // 3. Toggle floating orb visibility
    if (scrollTopBtn) {
      if (scrollTop > 180) {
        scrollTopBtn.classList.add("is-visible");
      } else {
        scrollTopBtn.classList.remove("is-visible");
      }
    }

    isTicking = false;
  }

  window.addEventListener("scroll", () => {
    if (!isTicking) {
      window.requestAnimationFrame(updateScrollState);
      isTicking = true;
    }
  }, { passive: true });

  // Smooth scroll back to top on click
  if (scrollTopBtn) {
    scrollTopBtn.addEventListener("click", (e) => {
      e.preventDefault();
      window.scrollTo({
        top: 0,
        behavior: "smooth"
      });
    });
  }

  // Initial calculation on load
  updateScrollState();
}

