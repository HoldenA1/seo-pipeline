import type { Schema, Struct } from '@strapi/strapi';

export interface UserContentSampleReview extends Struct.ComponentSchema {
  collectionName: 'components_user_content_sample_reviews';
  info: {
    displayName: 'SampleReview';
    icon: 'quote';
  };
  attributes: {
    AuthorName: Schema.Attribute.String;
    AuthorPhotoURL: Schema.Attribute.String;
    AuthorProfileURL: Schema.Attribute.String;
    Rating: Schema.Attribute.Integer &
      Schema.Attribute.SetMinMax<
        {
          max: 5;
          min: 1;
        },
        number
      >;
    Review: Schema.Attribute.Text;
    TimePublished: Schema.Attribute.DateTime;
  };
}

declare module '@strapi/strapi' {
  export module Public {
    export interface ComponentSchemas {
      'user-content.sample-review': UserContentSampleReview;
    }
  }
}
