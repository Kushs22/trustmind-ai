/** Client-side password rules — keep in sync with backend/app/core/passwords.py */

export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_LENGTH = 128;

export function validatePasswordStrength(password: string): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  if (password.length > MAX_PASSWORD_LENGTH) {
    return `Password must be at most ${MAX_PASSWORD_LENGTH} characters.`;
  }
  if (!/[A-Za-z]/.test(password)) {
    return "Password must include at least one letter.";
  }
  if (!/\d/.test(password) && !/[^A-Za-z0-9]/.test(password)) {
    return "Password must include at least one number or special character.";
  }
  return null;
}
