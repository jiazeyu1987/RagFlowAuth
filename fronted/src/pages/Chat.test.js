import React from 'react';
import { render, screen } from '@testing-library/react';

import Chat from './Chat';
import useChatPage from '../features/chat/useChatPage';

jest.mock('../features/chat/useChatPage', () => ({
  __esModule: true,
  default: jest.fn(),
}));

jest.mock('../features/chat/components/ChatSidebar', () => function MockChatSidebar() {
  return <div data-testid="mock-chat-sidebar" />;
});

jest.mock('../features/chat/components/ChatMessages', () => function MockChatMessages() {
  return <div data-testid="mock-chat-messages" />;
});

jest.mock('../features/chat/components/ChatComposer', () => function MockChatComposer() {
  return <div data-testid="mock-chat-composer" />;
});

jest.mock('../features/chat/components/dialogs/DeleteSessionDialog', () => function MockDeleteSessionDialog(props) {
  return props.open ? <div data-testid="mock-chat-delete-dialog">{props.sessionName}</div> : null;
});

jest.mock('../features/chat/components/dialogs/RenameSessionDialog', () => function MockRenameSessionDialog(props) {
  return props.open ? <div data-testid="mock-chat-rename-dialog">{props.value}</div> : null;
});

jest.mock('../features/chat/components/dialogs/CitationTooltip', () => function MockCitationTooltip(props) {
  return props.citationHover ? <div data-testid="mock-chat-citation-tooltip">{props.citationHover.chunk}</div> : null;
});

jest.mock('../shared/documents/preview/DocumentPreviewModal', () => ({
  DocumentPreviewModal: function MockDocumentPreviewModal(props) {
    return props.open ? <div data-testid="mock-chat-preview-modal">{props.target?.filename}</div> : null;
  },
}));

const createPageState = (overrides = {}) => ({
  canDownloadFiles: true,
  inputMessage: '',
  previewOpen: false,
  previewTarget: null,
  citationHover: null,
  isMobile: false,
  messagesEndRef: { current: null },
  chats: [{ id: 'chat-1', name: '质量助手' }],
  selectedChatId: 'chat-1',
  sessions: [{ id: 'session-1', name: '会话一' }],
  selectedSessionId: 'session-1',
  messages: [],
  loading: false,
  error: '',
  deleteConfirm: { show: false, sessionName: '' },
  renameDialog: { show: false, value: '' },
  setInputMessage: jest.fn(),
  setSelectedChatId: jest.fn(),
  createSession: jest.fn(),
  selectSession: jest.fn(),
  setError: jest.fn(),
  confirmDeleteSession: jest.fn(),
  closeDeleteConfirm: jest.fn(),
  confirmRenameSession: jest.fn(),
  closeRenameDialog: jest.fn(),
  closePreview: jest.fn(),
  sendMessage: jest.fn(),
  openSourcePreview: jest.fn(),
  downloadSource: jest.fn(),
  onCitationClick: jest.fn(),
  onCitationPopupLeave: jest.fn(),
  handleComposerKeyPress: jest.fn(),
  openRenameDialog: jest.fn(),
  openDeleteDialog: jest.fn(),
  setRenameDialogValue: jest.fn(),
  ...overrides,
});

describe('Chat', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useChatPage.mockReturnValue(createPageState());
  });

  it('renders the chat page shell from the page hook state', () => {
    useChatPage.mockReturnValue(
      createPageState({
        error: '发送失败',
      })
    );

    render(<Chat />);

    expect(screen.getByTestId('chat-page')).toBeInTheDocument();
    expect(screen.getByText('对话')).toBeInTheDocument();
    expect(screen.getByTestId('mock-chat-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('mock-chat-messages')).toBeInTheDocument();
    expect(screen.getByTestId('mock-chat-composer')).toBeInTheDocument();
    expect(screen.getByTestId('chat-error')).toHaveTextContent('发送失败');
  });

  it('passes modal and tooltip visibility through the page hook contract', () => {
    useChatPage.mockReturnValue(
      createPageState({
        previewOpen: true,
        previewTarget: { filename: 'Spec.pdf' },
        citationHover: { id: 1, chunk: '引用片段', x: 12, y: 24 },
        deleteConfirm: { show: true, sessionName: '会话一' },
        renameDialog: { show: true, value: '新会话名' },
      })
    );

    render(<Chat />);

    expect(screen.getByTestId('mock-chat-preview-modal')).toHaveTextContent('Spec.pdf');
    expect(screen.getByTestId('mock-chat-citation-tooltip')).toHaveTextContent('引用片段');
    expect(screen.getByTestId('mock-chat-delete-dialog')).toHaveTextContent('会话一');
    expect(screen.getByTestId('mock-chat-rename-dialog')).toHaveTextContent('新会话名');
  });
});
