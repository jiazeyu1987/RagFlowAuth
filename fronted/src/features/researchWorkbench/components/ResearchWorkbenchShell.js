import React from 'react';
import '../researchWorkbench.css';

export default function ResearchWorkbenchShell({
  leftPane,
  centerPane,
  rightPane,
  bottomPane,
  testId = 'research-workbench-shell',
}) {
  return (
    <div className="research-workbench-shell" data-testid={testId}>
      <div className="research-workbench-main">
        <aside className="research-workbench-panel research-workbench-left">
          {leftPane}
        </aside>
        <section className="research-workbench-panel research-workbench-center">
          {centerPane}
        </section>
        <aside className="research-workbench-panel research-workbench-right">
          {rightPane}
        </aside>
      </div>
      <section className="research-workbench-bottom">
        {bottomPane}
      </section>
    </div>
  );
}
