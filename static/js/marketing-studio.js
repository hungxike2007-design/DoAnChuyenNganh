/**
 * ==============================================================================
 * LOGIC AI MARKETING & TIKTOK SCRIPT STUDIO (MARKETING-STUDIO.JS)
 * Hệ Thống Phân Tích Doanh Thu AI - Đồ Án Chuyên Ngành
 * ==============================================================================
 */

let currentCampaignData = null;
let activeTab = 'tiktok';
let productsList = [];
let campaignHistory = [];

/**
 * Khởi tạo Studio khi trang tải xong
 */
async function initStudio() {
  await loadProductsDropdown();
  parseUrlParams();
  await loadCampaignHistory();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initStudio);
} else {
  initStudio();
}

/**
 * Tải danh sách sản phẩm từ backend để đưa vào dropdown
 */
async function loadProductsDropdown() {
  const selectEl = document.getElementById('select-product');
  if (!selectEl) return;

  try {
    const res = await apiRequest('/api/products/');
    if (res && res.success && Array.isArray(res.data) && res.data.length > 0) {
      productsList = res.data;
      selectEl.innerHTML = '<option value="">-- Chọn sản phẩm có sẵn trong kho (' + productsList.length + ' sản phẩm) --</option>' +
        productsList.map(p => {
          const price = p.selling_price || p.price || 0;
          return `<option value="${p.id}">${escapeHtml(p.name)} (${formatVND(price)})</option>`;
        }).join('');
    } else {
      selectEl.innerHTML = '<option value="">-- Tự nhập thông tin sản phẩm bên dưới --</option>';
    }
  } catch (err) {
    console.warn('Không tải được danh mục sản phẩm, chuyển sang chế độ nhập tay:', err);
    selectEl.innerHTML = '<option value="">-- Tự nhập thông tin sản phẩm bên dưới --</option>';
  }
}

/**
 * Đọc tham số URL (khi người dùng bấm chuyển tiếp từ Dashboard hoặc Kho Hàng)
 */
function parseUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const pId = params.get('product_id');
  const pName = params.get('product_name');
  const pPrice = params.get('price');
  const pCat = params.get('category');

  if (pName) {
    const nameInput = document.getElementById('input-product-name');
    if (nameInput) nameInput.value = pName;
  }
  if (pPrice) {
    const priceInput = document.getElementById('input-product-price');
    if (priceInput) priceInput.value = pPrice;
  }
  if (pCat) {
    const catInput = document.getElementById('input-product-category');
    if (catInput) catInput.value = pCat;
  }

  if (pId) {
    const selectEl = document.getElementById('select-product');
    if (selectEl) {
      selectEl.value = pId;
      if (selectEl.value) {
        onProductSelect(pId);
      }
    }
  }
}

/**
 * Xử lý khi người dùng chọn sản phẩm từ dropdown
 */
function onProductSelect(productId) {
  if (!productId) return;
  const product = productsList.find(p => String(p.id) === String(productId));
  if (!product) return;

  const nameInput = document.getElementById('input-product-name');
  const priceInput = document.getElementById('input-product-price');
  const catInput = document.getElementById('input-product-category');
  const audienceInput = document.getElementById('input-target-audience');

  if (nameInput) nameInput.value = product.name || '';
  if (priceInput) priceInput.value = product.selling_price || product.price || '';
  if (catInput) catInput.value = product.category_name || '';

  // Gợi ý tệp khách hàng theo danh mục nếu chưa có
  if (audienceInput && !audienceInput.value.trim()) {
    const catLower = (product.category_name || '').toLowerCase();
    if (catLower.includes('thời trang') || catLower.includes('quần') || catLower.includes('áo') || catLower.includes('giày')) {
      audienceInput.value = 'Giới trẻ Gen Z, nhân viên văn phòng năng động 18-35 tuổi';
    } else if (catLower.includes('công nghệ') || catLower.includes('điện tử') || catLower.includes('phụ kiện')) {
      audienceInput.value = 'Yêu thích công nghệ, game thủ, làm việc văn phòng cần đồ tiện ích';
    } else if (catLower.includes('gia dụng') || catLower.includes('bếp') || catLower.includes('nhà')) {
      audienceInput.value = 'Chủ gia đình, phụ nữ nội trợ, người sống độc thân thích tiện nghi';
    } else if (catLower.includes('mỹ phẩm') || catLower.includes('làm đẹp')) {
      audienceInput.value = 'Phái đẹp từ 18-40 tuổi quan tâm chăm sóc sức khỏe và ngoại hình';
    }
  }
}

/**
 * Gửi yêu cầu sinh chiến dịch AI Marketing tới backend
 */
async function generateCampaign() {
  const productName = document.getElementById('input-product-name').value.trim();
  const price = parseFloat(document.getElementById('input-product-price').value) || null;
  const category = document.getElementById('input-product-category').value.trim();
  const targetAudience = document.getElementById('input-target-audience').value.trim();

  const goalEl = document.querySelector('input[name="campaign_goal"]:checked');
  const campaignGoal = goalEl ? goalEl.value : 'sales_boost';

  const toneEl = document.querySelector('input[name="campaign_tone"]:checked');
  const campaignTone = toneEl ? toneEl.value : 'trendy';

  if (!productName) {
    showToast('Vui lòng nhập tên sản phẩm trước khi xuất bản!', 'error');
    document.getElementById('input-product-name').focus();
    return;
  }

  // Chuyển đổi trạng thái giao diện sang loading
  const emptyState = document.getElementById('studio-empty-state');
  const loadingState = document.getElementById('studio-loading-state');
  const resultContainer = document.getElementById('studio-result-container');
  const btnGenerate = document.getElementById('btn-generate-campaign');

  if (emptyState) emptyState.style.display = 'none';
  if (resultContainer) resultContainer.style.display = 'none';
  if (loadingState) loadingState.style.display = 'block';

  if (btnGenerate) {
    btnGenerate.disabled = true;
    btnGenerate.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang Phân Tích & Sáng Tạo...';
  }

  try {
    const payload = {
      product_name: productName,
      price: price,
      category: category,
      target_audience: targetAudience,
      campaign_goal: campaignGoal,
      campaign_tone: campaignTone
    };

    const res = await apiRequest('/api/ai/marketing-campaign', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res.success && res.data) {
      currentCampaignData = res.data;
      renderCampaignResult(res.data);
      if (loadingState) loadingState.style.display = 'none';
      if (resultContainer) resultContainer.style.display = 'block';
      showToast('Kịch bản video & content quảng cáo đã sẵn sàng!', 'success');
      // Tải lại danh sách lịch sử chiến dịch
      loadCampaignHistory();
    } else {
      throw new Error(res.message || 'Không thể tạo kịch bản từ AI');
    }
  } catch (err) {
    console.error('Lỗi sinh chiến dịch:', err);
    showToast('Lỗi khi sinh kịch bản: ' + err.message, 'error');
    if (loadingState) loadingState.style.display = 'none';
    if (emptyState && !currentCampaignData) emptyState.style.display = 'block';
    if (resultContainer && currentCampaignData) resultContainer.style.display = 'block';
  } finally {
    if (btnGenerate) {
      btnGenerate.disabled = false;
      btnGenerate.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Xuất Bản Kịch Bản & Content (Gemini)';
    }
  }
}

/**
 * Hiển thị toàn bộ kết quả chiến dịch lên màn hình
 */
function renderCampaignResult(data) {
  // 1. Header & Selling Points
  const titleEl = document.getElementById('result-campaign-title');
  if (titleEl) titleEl.textContent = data.campaign_title || 'Chiến Dịch Sản Phẩm Đột Phá';

  const uspContainer = document.getElementById('result-selling-points');
  if (uspContainer && Array.isArray(data.selling_points)) {
    uspContainer.innerHTML = data.selling_points.map(point => `
      <span class="badge-tag" style="background:#eef2ff; color:#4338ca; border:1px solid #c7d2fe; font-size:12px; font-weight:600;">
        <i class="fa-solid fa-check" style="margin-right:4px; font-size:10px;"></i> ${escapeHtml(point)}
      </span>
    `).join('');
  }

  // 2. Tab 1: Kịch bản TikTok 30s
  const script = data.video_script || {};
  const musicEl = document.getElementById('script-music-vibe');
  const hookEl = document.getElementById('script-hook-type');
  if (musicEl) musicEl.textContent = script.music_vibe || 'Remix Trend TikTok sôi động';
  if (hookEl) hookEl.textContent = script.hook_type || script.hook_technique || 'Gây shock tò mò';

  const storyboard = script.storyboard || script.scenes || [];
  const storyboardContainer = document.getElementById('timeline-scenes-list');
  if (storyboardContainer && Array.isArray(storyboard)) {
    storyboardContainer.innerHTML = storyboard.map((scene, idx) => {
      const colors = [
        { bg: '#fee2e2', text: '#991b1b', border: '#ef4444' }, // Hook: Đỏ cảnh báo
        { bg: '#fef3c7', text: '#92400e', border: '#f59e0b' }, // Pain: Vàng chú ý
        { bg: '#e0e7ff', text: '#3730a3', border: '#6366f1' }, // Solution: Tím giải pháp
        { bg: '#dcfce7', text: '#166534', border: '#22c55e' }  // CTA: Xanh chốt đơn
      ];
      const color = colors[idx % colors.length];
      const sceneTitle = scene.title || (idx === 0 ? 'HOOK 3 GIÂY' : idx === 1 ? 'NỖI ĐAU KHÁCH HÀNG' : idx === 2 ? 'GIẢI PHÁP ĐỘT PHÁ' : 'KÊU GỌI HÀNH ĐỘNG (CTA)');

      return `
        <div class="scene-card" style="border-left-color: ${color.border};">
          <div class="scene-header">
            <span class="scene-badge" style="background:${color.bg}; color:${color.text};">
              CẢNH ${scene.scene || (idx + 1)}: ${escapeHtml(sceneTitle)}
            </span>
            <span style="font-size:12px; font-weight:700; color:var(--text-muted); background:#f1f5f9; padding:2px 8px; border-radius:12px;">
              <i class="fa-regular fa-clock" style="margin-right:3px;"></i> ${escapeHtml(scene.time || `Cảnh ${idx + 1}`)}
            </span>
          </div>

          <div class="scene-body-row">
            <span class="scene-label"><i class="fa-solid fa-video" style="color:#6366f1; margin-right:4px;"></i> Hình ảnh:</span>
            <span style="color:var(--text-primary);">${escapeHtml(scene.visual || '')}</span>
          </div>

          <div class="scene-body-row">
            <span class="scene-label"><i class="fa-solid fa-microphone-lines" style="color:#ef4444; margin-right:4px;"></i> Lời thoại:</span>
            <span style="font-weight:700; color:#1e1b4b; background:#f8fafc; padding:4px 8px; border-radius:4px; border:1px dashed #cbd5e1;">
              "${escapeHtml(scene.voiceover || '')}"
            </span>
          </div>

          <div class="scene-body-row" style="margin-bottom:0;">
            <span class="scene-label"><i class="fa-solid fa-closed-captioning" style="color:#10b981; margin-right:4px;"></i> Chữ màn hình:</span>
            <span style="color:var(--text-secondary); font-size:12.5px;">
              <code style="background:#f1f5f9; padding:2px 6px; border-radius:3px; color:#0f172a; font-weight:600;">
                ${escapeHtml(scene.text_overlay || '')}
              </code>
            </span>
          </div>
        </div>
      `;
    }).join('');
  }

  // 3. Tab 2: Facebook Ads AIDA
  const ad = data.social_ad || {};
  const fbBody = document.getElementById('fb-post-content');
  const fbCta = document.getElementById('fb-post-cta');
  if (fbBody) fbBody.textContent = ad.primary_text || ad.body || '';
  if (fbCta) fbCta.textContent = ad.call_to_action || 'NHẬN ƯU ĐÃI NGAY';

  // 4. Tab 3: SEO Pack
  const seo = data.seo_pack || {};
  const shopeeTitleEl = document.getElementById('seo-shopee-title');
  const titleCountEl = document.getElementById('seo-title-count');
  if (shopeeTitleEl) {
    const titleVal = seo.shopee_title || '';
    shopeeTitleEl.value = titleVal;
    if (titleCountEl) {
      titleCountEl.textContent = `Độ dài: ${titleVal.length} ký tự (Khuyến nghị chuẩn SEO: 60 - 120 ký tự)`;
    }
  }

  const hashtags = seo.hashtags || ad.hashtags || [];
  const hashContainer = document.getElementById('seo-hashtags-container');
  if (hashContainer && Array.isArray(hashtags)) {
    hashContainer.innerHTML = hashtags.map(tag => `
      <span class="badge-tag" style="background:#f0fdf4; color:#166534; border:1px solid #bbf7d0; cursor:pointer; font-size:12.5px; padding:5px 10px;" onclick="copySingleTag('${escapeHtml(tag)}')" title="Bấm để sao chép">
        <i class="fa-solid fa-copy" style="font-size:11px; margin-right:4px; opacity:0.7;"></i> ${escapeHtml(tag)}
      </span>
    `).join('');
  }

  const keywords = seo.target_keywords || seo.keywords || [];
  const kwContainer = document.getElementById('seo-keywords-container');
  if (kwContainer && Array.isArray(keywords)) {
    kwContainer.innerHTML = keywords.map(kw => `
      <span class="badge-tag" style="background:#fffbeb; color:#92400e; border:1px solid #fde68a; font-size:12px; padding:4px 8px;">
        <i class="fa-solid fa-magnifying-glass" style="font-size:10px; margin-right:4px; opacity:0.7;"></i> ${escapeHtml(kw)}
      </span>
    `).join('');
  }
}

/**
 * Tải danh sách lịch sử các chiến dịch kịch bản đã lưu
 */
async function loadCampaignHistory() {
  const container = document.getElementById('marketing-history-list');
  if (!container) return;

  try {
    const res = await apiRequest('/api/ai/marketing-history?limit=10');
    if (res && res.success && Array.isArray(res.data) && res.data.length > 0) {
      campaignHistory = res.data;
      container.innerHTML = campaignHistory.map(item => {
        const title = escapeHtml(item.title || 'Chiến dịch');
        const prod = escapeHtml(item.user_prompt || 'Sản phẩm');
        const dateStr = item.created_at ? item.created_at.slice(5, 16) : '';

        return `
          <div onclick="selectHistoryCampaign(${item.id})" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:8px 10px; cursor:pointer; transition:all 0.15s ease;" onmouseover="this.style.borderColor='var(--accent-primary)'; this.style.background='#f0f9ff';" onmouseout="this.style.borderColor='#e2e8f0'; this.style.background='#f8fafc';">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">
              <b style="font-size:12px; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:210px;" title="${title}">${title}</b>
              <span style="font-size:10.5px; color:var(--text-muted);">${dateStr}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:11.5px; color:var(--text-secondary);">
              <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:200px;">
                <i class="fa-solid fa-box" style="font-size:10px; color:var(--accent-primary); margin-right:3px;"></i> ${prod}
              </span>
              <button onclick="deleteHistoryCampaign(event, ${item.id})" style="background:none; border:none; color:#ef4444; cursor:pointer; padding:2px 4px; font-size:11px;" title="Xóa bản ghi này">
                <i class="fa-regular fa-trash-can"></i>
              </button>
            </div>
          </div>
        `;
      }).join('');
    } else {
      container.innerHTML = '<p style="color:var(--text-muted); font-size:12px; margin:0; text-align:center; padding:12px 0;">Chưa có kịch bản nào được lưu.</p>';
    }
  } catch (err) {
    console.warn('Lỗi tải lịch sử kịch bản:', err);
    container.innerHTML = '<p style="color:var(--text-muted); font-size:12px; margin:0; text-align:center; padding:12px 0;">Không thể tải lịch sử.</p>';
  }
}

/**
 * Chọn và xem lại một kịch bản từ lịch sử
 */
function selectHistoryCampaign(historyId) {
  const item = campaignHistory.find(h => h.id === historyId);
  if (!item || !item.ai_response) {
    showToast('Không tìm thấy dữ liệu kịch bản này!', 'error');
    return;
  }

  // Điền lại các ô input nếu có metrics_context
  if (item.metrics_context) {
    const mc = item.metrics_context;
    if (mc.product_name) {
      const nameInput = document.getElementById('input-product-name');
      if (nameInput) nameInput.value = mc.product_name;
    }
    if (mc.price) {
      const priceInput = document.getElementById('input-product-price');
      if (priceInput) priceInput.value = mc.price;
    }
    if (mc.category) {
      const catInput = document.getElementById('input-product-category');
      if (catInput) catInput.value = mc.category;
    }
    if (mc.goal) {
      const goalRadio = document.querySelector(`input[name="campaign_goal"][value="${mc.goal}"]`);
      if (goalRadio) goalRadio.checked = true;
    }
    if (mc.tone) {
      const toneRadio = document.querySelector(`input[name="campaign_tone"][value="${mc.tone}"]`);
      if (toneRadio) toneRadio.checked = true;
    }
  }

  // Hiển thị kết quả kịch bản
  currentCampaignData = item.ai_response;
  renderCampaignResult(item.ai_response);

  const emptyState = document.getElementById('studio-empty-state');
  const loadingState = document.getElementById('studio-loading-state');
  const resultContainer = document.getElementById('studio-result-container');

  if (emptyState) emptyState.style.display = 'none';
  if (loadingState) loadingState.style.display = 'none';
  if (resultContainer) resultContainer.style.display = 'block';

  showToast('Đã tải kịch bản từ lịch sử lưu trữ!', 'info');
}

/**
 * Xóa một bản ghi lịch sử
 */
async function deleteHistoryCampaign(event, historyId) {
  if (event) event.stopPropagation();
  if (!confirm('Bạn có chắc chắn muốn xóa kịch bản này khỏi lịch sử?')) return;

  try {
    const res = await apiRequest(`/api/ai/marketing-history/${historyId}`, { method: 'DELETE' });
    if (res && res.success) {
      showToast('Đã xóa kịch bản khỏi lịch sử!', 'success');
      loadCampaignHistory();
    } else {
      showToast('Lỗi khi xóa: ' + (res.message || 'Không thể xóa'), 'error');
    }
  } catch (err) {
    showToast('Lỗi khi xóa lịch sử: ' + err.message, 'error');
  }
}

/**
 * Chuyển đổi giữa 3 Tab hiển thị kết quả
 */
function switchStudioTab(tab) {
  activeTab = tab;
  ['tiktok', 'facebook', 'seo'].forEach(t => {
    const btn = document.getElementById(`tab-btn-${t}`);
    const content = document.getElementById(`tab-content-${t}`);
    if (btn) btn.classList.toggle('active', t === tab);
    if (content) content.style.display = (t === tab) ? 'block' : 'none';
  });
}

/**
 * Sao chép nội dung của Tab hiện tại vào Clipboard
 */
function copyCurrentTabContent() {
  if (!currentCampaignData) {
    showToast('Không có nội dung để sao chép!', 'error');
    return;
  }

  let textToCopy = '';
  if (activeTab === 'tiktok') {
    const script = currentCampaignData.video_script || {};
    const sb = script.storyboard || script.scenes || [];
    textToCopy = `🎬 KỊCH BẢN VIDEO TIKTOK 30s: ${currentCampaignData.campaign_title}\n` +
      `Nhạc nền: ${script.music_vibe || 'Sôi động'}\n\n` +
      sb.map((s, idx) => `[Cảnh ${idx + 1} (${s.time || ''})] ${s.title || ''}\n- Hình ảnh: ${s.visual}\n- Lời thoại: "${s.voiceover}"\n- Chữ màn hình: ${s.text_overlay}`).join('\n\n');
  } else if (activeTab === 'facebook') {
    const ad = currentCampaignData.social_ad || {};
    textToCopy = ad.primary_text || ad.body || '';
  } else if (activeTab === 'seo') {
    const seo = currentCampaignData.seo_pack || {};
    const ad = currentCampaignData.social_ad || {};
    const hashtags = seo.hashtags || ad.hashtags || [];
    const keywords = seo.target_keywords || seo.keywords || [];
    textToCopy = `Tiêu đề Shopee/TikTok Shop: ${seo.shopee_title}\n\nHashtags:\n${hashtags.join(' ')}\n\nTừ khóa SEO:\n${keywords.join(', ')}`;
  }

  copyToClipboard(textToCopy, 'Đã sao chép nội dung tab hiện tại!');
}

/**
 * Sao chép bài viết Facebook
 */
function copyFacebookPost() {
  if (!currentCampaignData || !currentCampaignData.social_ad) return;
  const ad = currentCampaignData.social_ad;
  copyToClipboard(ad.primary_text || ad.body || '', 'Đã sao chép bài viết Facebook Ads!');
}

/**
 * Sao chép tiêu đề Shopee chuẩn SEO
 */
function copyShopeeTitle() {
  const titleInput = document.getElementById('seo-shopee-title');
  if (!titleInput || !titleInput.value) return;
  copyToClipboard(titleInput.value, 'Đã sao chép tiêu đề chuẩn SEO!');
}

/**
 * Sao chép 1 hashtag cụ thể
 */
function copySingleTag(tag) {
  copyToClipboard(tag, `Đã chép hashtag ${tag}!`);
}

/**
 * Xuất toàn bộ chiến dịch ra file .txt
 */
function exportScriptText() {
  if (!currentCampaignData) {
    showToast('Chưa có dữ liệu chiến dịch để xuất file!', 'error');
    return;
  }

  const d = currentCampaignData;
  const script = d.video_script || {};
  const sb = script.storyboard || script.scenes || [];
  const ad = d.social_ad || {};
  const seo = d.seo_pack || {};
  const hashtags = seo.hashtags || ad.hashtags || [];
  const keywords = seo.target_keywords || seo.keywords || [];

  const fullReport = `======================================================================
BẢN KẾ HOẠCH MARKETING & KỊCH BẢN TIKTOK TỰ ĐỘNG - GEMINI AI
Hệ Thống Phân Tích Doanh Thu AI
======================================================================

1. CHIẾN DỊCH: ${d.campaign_title}
- Điểm bán hàng độc nhất (USP):
${(d.selling_points || []).map(p => `  * ${p}`).join('\n')}

======================================================================
2. KỊCH BẢN VIDEO TIKTOK 30 GIÂY
Nhạc nền đề xuất: ${script.music_vibe || 'Sôi động'}
Loại hình Hook 3s: ${script.hook_type || script.hook_technique || 'Gây tò mò'}

${sb.map((s, idx) => `[PHÂN CẢNH ${idx + 1} (${s.time || ''})] - ${s.title || ''}
* Hình ảnh / Hành động: ${s.visual}
* Lời thoại MC: "${s.voiceover}"
* Chữ hiển thị màn hình: ${s.text_overlay}
----------------------------------------------------------------------`).join('\n')}

======================================================================
3. BÀI VIẾT QUẢNG CÁO FACEBOOK ADS (CHUẨN AIDA)
${ad.primary_text || ad.body || ''}

Nút kêu gọi hành động (CTA): ${ad.call_to_action || 'MUA NGAY'}

======================================================================
4. BỘ TỐI ƯU TÌM KIẾM (SEO PACK)
- Tiêu đề Shopee / TikTok Shop:
  ${seo.shopee_title || ''}

- Bộ Hashtags thịnh hành:
  ${hashtags.join(' ')}

- Từ khóa tìm kiếm tự nhiên:
  ${keywords.join(', ')}

======================================================================
Xuất bản lúc: ${new Date().toLocaleString('vi-VN')}
Được tạo bởi AI Marketing Studio.
`;

  const blob = new Blob([fullReport], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const fileName = `Kich_Ban_Marketing_${(d.campaign_title || 'AI').replace(/[^a-zA-Z0-9_\u00C0-\u024F\u1E00-\u1EFF]/g, '_')}.txt`;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('Đã tải xuống file kịch bản thành công!', 'success');
}

/**
 * Helper sao chép text và thông báo
 */
function copyToClipboard(text, successMsg) {
  if (!text) return;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(successMsg, 'success');
    }).catch(err => {
      fallbackCopyText(text, successMsg);
    });
  } else {
    fallbackCopyText(text, successMsg);
  }
}

function fallbackCopyText(text, successMsg) {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';
  textArea.style.top = '-999999px';
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  try {
    document.execCommand('copy');
    showToast(successMsg, 'success');
  } catch (err) {
    showToast('Không thể sao chép tự động: ' + err, 'error');
  }
  document.body.removeChild(textArea);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
