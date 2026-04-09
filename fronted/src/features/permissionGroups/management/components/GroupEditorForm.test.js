import React from 'react';
import { render, screen } from '@testing-library/react';
import GroupEditorForm from './GroupEditorForm';

const makeProps = () => ({
  loading: false,
  mode: 'edit',
  formData: {
    group_name: 'Group A',
    description: 'desc',
    accessible_kbs: [],
    accessible_chats: [],
    can_upload: true,
    can_review: true,
    can_download: true,
    can_copy: false,
    can_delete: false,
    can_view_kb_config: true,
  },
  editingGroup: { group_id: 1, group_name: 'Group A' },
  saving: false,
  knowledgeDatasetItems: [],
  chatAgents: [],
  onSetFormData: jest.fn(),
  onToggleKbAuth: jest.fn(),
  onToggleChatAuth: jest.fn(),
  onSaveForm: jest.fn((event) => event.preventDefault()),
  onCancelEdit: jest.fn(),
});

describe('GroupEditorForm', () => {
  it('renders kb/chat/action sections and no removed tool config fields', () => {
    render(<GroupEditorForm {...makeProps()} />);

    expect(screen.getByTestId('pg-form-can-upload')).toBeInTheDocument();
    expect(screen.getByTestId('pg-form-can-download')).toBeInTheDocument();
    expect(screen.queryByTestId('pg-form-can-view-tools')).not.toBeInTheDocument();
    expect(screen.queryByTestId('pg-form-can-review')).not.toBeInTheDocument();
    expect(screen.queryByTestId('pg-form-can-view-kb-config')).not.toBeInTheDocument();
  });
});
