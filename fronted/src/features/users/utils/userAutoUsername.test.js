import {
  buildAutoUsernameFromFullName,
  normalizeAutoUsername,
  shouldApplyAutoUsername,
} from './userAutoUsername';

describe('userAutoUsername', () => {
  it('builds lowercase pinyin usernames without separators', () => {
    expect(buildAutoUsernameFromFullName('张三')).toBe('zhangsan');
    expect(buildAutoUsernameFromFullName('曾乐乐')).toBe('zenglele');
    expect(buildAutoUsernameFromFullName('吕布')).toBe('lvbu');
  });

  it('keeps ascii letters and digits while removing other characters', () => {
    expect(buildAutoUsernameFromFullName('A张-三 007')).toBe('azhangsan007');
    expect(normalizeAutoUsername('A zhang-san_007')).toBe('azhangsan007');
  });

  it('returns empty string when no valid username characters remain', () => {
    expect(buildAutoUsernameFromFullName('!!!')).toBe('');
    expect(buildAutoUsernameFromFullName('   ')).toBe('');
  });

  it('only overwrites empty or previously auto-generated usernames', () => {
    expect(shouldApplyAutoUsername({ currentUsername: '', lastAutoUsername: 'zhangsan' })).toBe(true);
    expect(
      shouldApplyAutoUsername({ currentUsername: 'zhangsan', lastAutoUsername: 'zhangsan' })
    ).toBe(true);
    expect(
      shouldApplyAutoUsername({ currentUsername: 'custom_account', lastAutoUsername: 'zhangsan' })
    ).toBe(false);
  });
});
