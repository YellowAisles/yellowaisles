import React from 'react';
import { connect } from 'react-redux';

const mapStateToProps = state => ({
});

const mapDispatchToProps = dispatch => ({
});

class Home extends React.Component {
  render() {
    return (
      <section class='yellow-aisles-main'>
        <h2>Yellow Aisles</h2>
        <p>Welcome</p>
      </section>
    );
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(Home);
