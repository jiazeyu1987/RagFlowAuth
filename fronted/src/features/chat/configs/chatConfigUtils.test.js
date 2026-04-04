import { sanitizeChatPayload } from './chatConfigUtils';

describe('chatConfigUtils', () => {
  it('removes hidden parsed-file bindings from chat payloads', () => {
    const sanitized = sanitizeChatPayload({
      id: 'c1',
      name: 'Chat',
      dataset_ids: ['ds1'],
      parsed_files: ['pf1'],
      parsed_file_id: 'pf_single',
      file_parsed_owner: 'legacy',
    });

    expect(sanitized).toEqual({
      name: 'Chat',
      dataset_ids: ['ds1'],
    });
  });
});
