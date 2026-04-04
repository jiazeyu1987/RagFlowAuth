import React from 'react';
import { render, screen } from '@testing-library/react';
import GroupEditorForm from './GroupEditorForm';

const makeProps = () => ({
  loading: false,
  formData: {
    group_name: 'Group A',
    description: 'desc',
    accessible_kbs: [],
    accessible_chats: [],
    accessible_tools: [],
    can_upload: true,
    can_review: true,
    can_download: true,
    can_copy: false,
    can_delete: false,
    can_view_kb_config: true,
    can_view_tools: true,
  },
  editingGroup: null,
  saving: false,
  knowledgeDatasetItems: [],
  chatAgents: [],
  onSetFormData: jest.fn(),
  onToggleKbAuth: jest.fn(),
  onToggleChatAuth: jest.fn(),
  onToggleToolAuth: jest.fn(),
  onSaveForm: jest.fn((event) => event.preventDefault()),
  onCancelEdit: jest.fn(),
});

describe('GroupEditorForm', () => {
  it('does not render removed operation permissions', () => {
    render(<GroupEditorForm {...makeProps()} />);

    expect(screen.queryByTestId('pg-form-can-review')).not.toBeInTheDocument();
    expect(screen.queryByTestId('pg-form-can-view-kb-config')).not.toBeInTheDocument();
    expect(screen.getByTestId('pg-form-can-upload')).toBeInTheDocument();
    expect(screen.getByTestId('pg-form-can-download')).toBeInTheDocument();
    expect(screen.getByTestId('pg-form-can-view-tools')).toBeInTheDocument();
  });
});
