import React from 'react';
import { useNavigate } from 'react-router-dom';

function openUrl(url) {
  window.open(url, '_blank', 'noopener,noreferrer');
}

export default function NMPATool() {
  const navigate = useNavigate();

  return (
    <div className="admin-med-page" data-testid="nmpa-tool-page">
      <section className="medui-surface medui-card-pad">
        <div className="admin-med-head">
          <div>
            <h2 className="admin-med-title" style={{ margin: 0 }}>国家药监局工具</h2>
            <div className="admin-med-inline-note" style={{ marginTop: 6 }}>
              国家药品监督管理局器审中心常用入口。
            </div>
          </div>
          <button type="button" onClick={() => navigate('/tools')} className="medui-btn medui-btn--secondary">
            返回实用工具
          </button>
        </div>
      </section>

      <section className="medui-surface medui-card-pad">
        <div className="admin-med-actions">
          <button
            type="button"
            onClick={() => openUrl('https://www.cmde.org.cn/index.html')}
            className="medui-btn medui-btn--primary"
            data-testid="nmpa-home-btn"
          >
            打开首页
          </button>
          <button
            type="button"
            onClick={() => openUrl('https://www.cmde.org.cn/flfg/zdyz/flmlbzh/flmlylqx/index.html')}
            className="medui-btn medui-btn--secondary"
            data-testid="nmpa-catalog-btn"
          >
            打开分类目录
          </button>
        </div>
      </section>
    </div>
  );
}
