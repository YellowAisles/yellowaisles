import React from 'react';

const App = ({ children }) => (
  <div className='content'>
    <div className='container-container'>
      <div>Test</div>
      {children}
    </div>
  </div>
);

export default App;
