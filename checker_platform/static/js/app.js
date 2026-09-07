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
}

function highlightTelcoBox(telcoKey) {
  document.querySelectorAll(".telco-radio-box").forEach(box => {
    box.style.borderColor = "var(--border-subtle)";
  });
  const targetBox = document.getElementById(`box_${telcoKey}`);
  if (targetBox) {
    targetBox.style.borderColor = "var(--ghana-gold)";
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

// Show MoMo USSD Prompt Screen
function showPaymentPrompt(data) {
  document.getElementById("checkout_step_details").style.display = "none";
  document.getElementById("checkout_step_payment").style.display = "block";

  const promptInfo = data.payment_prompt;
  document.getElementById("momo_display_network").innerText = promptInfo.network;
  document.getElementById("momo_display_phone").innerText = promptInfo.phone_formatted;
  document.getElementById("momo_display_amount").innerText = `GHS ${promptInfo.amount_ghs.toFixed(2)}`;
  document.getElementById("momo_display_order_ref").innerText = data.order.order_reference;
  document.getElementById("momo_prompt_instructions").innerText = promptInfo.prompt_text;
  document.getElementById("momo_manual_steps").innerText = promptInfo.manual_steps;
}

// Complete / Simulate Approval
async function approveSimulatedPayment() {
  if (!currentOrder) return;
  const btn = document.getElementById("btn_approve_payment");
  btn.innerText = "Verifying Transaction...";
  btn.disabled = true;

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
      btn.innerText = "Approve & Complete (Test)";
      btn.disabled = false;
      return;
    }

    showSuccessVouchers(data);
  } catch (err) {
    alert("Verification error: " + err.message);
    btn.innerText = "Approve & Complete (Test)";
    btn.disabled = false;
  }
}

// Render Sold Vouchers on Screen
function showSuccessVouchers(data) {
  document.getElementById("checkout_step_payment").style.display = "none";
  document.getElementById("checkout_step_success").style.display = "block";

  const container = document.getElementById("vouchers_container");
  container.innerHTML = "";

  const fulfillment = data.fulfillment;
  document.getElementById("success_order_ref").innerText = fulfillment.order_reference;

  fulfillment.cards.forEach((c) => {
    const cardHtml = `
      <div class="voucher-reveal-card">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
          <span style="font-weight: 700; color: var(--ghana-gold);">${fulfillment.category_title} (Card #${c.item_number})</span>
          <span style="font-size: 0.8rem; color: var(--ghana-green); font-weight: 700;">ACTIVE / VALID</span>
        </div>
        
        <div class="voucher-field">
          <div>
            <div class="voucher-field-label">Serial Number</div>
            <div class="voucher-val" id="serial_${c.item_number}">${c.serial_number}</div>
          </div>
          <button class="btn-copy" onclick="copyText('${c.serial_number}', this)">Copy Serial</button>
        </div>

        <div class="voucher-field">
          <div>
            <div class="voucher-field-label">Voucher PIN</div>
            <div class="voucher-val" id="pin_${c.item_number}">${c.pin}</div>
          </div>
          <button class="btn-copy" onclick="copyText('${c.pin}', this)">Copy PIN</button>
        </div>
      </div>
    `;
    container.innerHTML += cardHtml;
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
