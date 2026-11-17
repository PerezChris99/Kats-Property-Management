import { Link } from 'react-router-dom';
import { Send } from 'lucide-react';

/** Encouraging labels change only visually; accessible link purpose remains stable. */
export function VictoryLink({ to, label, winText, className = '' }) {
  return <Link to={to} aria-label={label}
    className={'button kats-victory-cta ' + className}>
    <span className="kats-victory-copy" aria-hidden="true">
      <span className="kats-victory-default">{label}</span>
      <span className="kats-victory-win">{winText}</span>
    </span>
    <span className="kats-victory-send" aria-hidden="true">
      <Send size={17} strokeWidth={1.9}/>
    </span>
  </Link>;
}
