import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import KnowledgeRootNodeSelector from './KnowledgeRootNodeSelector';

describe('KnowledgeRootNodeSelector', () => {
  it('disables occupied container selection while keeping expand and free-child selection available', async () => {
    const user = userEvent.setup();
    const onSelect = jest.fn();

    render(
      <KnowledgeRootNodeSelector
        nodes={[
          { id: 'node-root-a', name: 'Root A', parent_id: '', path: '/Root A' },
          { id: 'node-root-a-free', name: 'Free Child', parent_id: 'node-root-a', path: '/Root A/Free Child' },
        ]}
        disabledNodeIds={['node-root-a']}
        selectedNodeId=""
        onSelect={onSelect}
      />
    );

    expect(screen.getByTestId('users-kb-root-node-node-root-a')).toBeDisabled();
    expect(screen.queryByTestId('users-kb-root-node-node-root-a-free')).not.toBeInTheDocument();

    await user.click(screen.getByTestId('users-kb-root-toggle-node-root-a'));

    expect(screen.getByTestId('users-kb-root-node-node-root-a-free')).toBeEnabled();

    await user.click(screen.getByTestId('users-kb-root-node-node-root-a-free'));

    expect(onSelect).toHaveBeenCalledWith('node-root-a-free');
  });
});
