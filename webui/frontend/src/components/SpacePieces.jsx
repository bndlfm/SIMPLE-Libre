import React from 'react';
import { SPACE_HITBOXES } from '../mapLayout';

export default function SpacePieces({ board }) {
  if (!board || !board.spaces) return null;

  return (
    <>
      {board.spaces.map((space) => {
        const hb = SPACE_HITBOXES.find(h => h.id === space.id);
        if (!hb) return null;

        return (
          <div
            key={`pieces-${space.id}`}
            style={{
              position: 'absolute',
              left: `${hb.x}%`,
              top: `${hb.y}%`,
              width: `${hb.w}%`,
              height: `${hb.h}%`,
              pointerEvents: 'none',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '2px',
              padding: '4px',
              boxSizing: 'border-box',
              alignContent: 'flex-start',
              overflow: 'hidden'
            }}
          >
            {space.pieces.map((count, idx) => {
              if (count === 0) return null;

              let typeClass = '';
              let isUnderground = false;

              // Correct Piece indices according to constants.py & env.py mapping
              // 0: Govt Troops
              // 1: Govt Police
              // 2: M26 Underground
              // 3: M26 Active
              // 4: M26 Bases
              // 5: DR Underground
              // 6: DR Active
              // 7: DR Bases
              // 8: Synd Underground
              // 9: Synd Active
              // 10: Synd Casinos (Bases)
              // (Govt Bases are space.govt_bases handled below)

              if (idx === 0) { typeClass = 'cube light-blue'; }
              else if (idx === 1) { typeClass = 'cylinder light-blue'; }
              else if (idx === 2) { typeClass = 'cube red'; isUnderground = true; }
              else if (idx === 3) { typeClass = 'cube red'; }
              else if (idx === 4) { typeClass = 'oct red'; }
              else if (idx === 5) { typeClass = 'cube yellow'; isUnderground = true; }
              else if (idx === 6) { typeClass = 'cube yellow'; }
              else if (idx === 7) { typeClass = 'oct yellow'; }
              else if (idx === 8) { typeClass = 'cube green'; isUnderground = true; }
              else if (idx === 9) { typeClass = 'cube green'; }
              else if (idx === 10) { typeClass = 'oct green'; }
              else return null;

              const colors = {
                'light-blue': '#87ceeb',
                'red': '#ff4040',
                'yellow': '#ffd700',
                'green': '#32cd32'
              };

              const shapeClass = typeClass.split(' ')[0] || 'cube';
              const colorClass = typeClass.split(' ')[1] || 'black';

              const isOct = shapeClass === 'oct';
              const isCyl = shapeClass === 'cylinder';

              return Array.from({ length: count }).map((_, i) => (
                <div
                  key={`p-${idx}-${i}`}
                  style={{
                    width: '12px',
                    height: '12px',
                    backgroundColor: isUnderground ? 'transparent' : colors[colorClass],
                    opacity: 1.0,
                    border: isUnderground ? `2px dashed ${colors[colorClass]}` : '1px solid black',
                    borderRadius: isCyl ? '50%' : isOct ? '3px' : '0',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '8px',
                    fontWeight: 'bold',
                    color: colorClass === 'yellow' ? 'black' : 'white',
                    boxShadow: isUnderground ? 'none' : '1px 1px 2px rgba(0,0,0,0.5)'
                  }}
                >
                  {isOct ? 'B' : ''}
                </div>
              ));
            })}

            {/* Govt Bases are stored separately in space.govt_bases */}
            {space.govt_bases > 0 && Array.from({ length: space.govt_bases }).map((_, i) => (
               <div
                 key={`gb-${i}`}
                 style={{
                   width: '12px',
                   height: '12px',
                   backgroundColor: '#87ceeb',
                   opacity: 1.0,
                   border: '1px solid black',
                   borderRadius: '3px',
                   display: 'flex',
                   alignItems: 'center',
                   justifyContent: 'center',
                   fontSize: '8px',
                   fontWeight: 'bold',
                   color: 'white',
                   boxShadow: '1px 1px 2px rgba(0,0,0,0.5)'
                 }}
               >
                 B
               </div>
            ))}
          </div>
        );
      })}
    </>
  );
}
